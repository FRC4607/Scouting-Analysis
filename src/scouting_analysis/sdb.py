"""The 4607 Scouting Database Module"""

import logging
from pathlib import Path

import pandas as pd
import requests

from .constants import (
    PITS_DATABASE_FILENAME,
    PITS_DATABASE_URL,
    SCOUTING_DATABASE_FILENAME,
    SCOUTING_DATABASE_URL,
)

logger = logging.getLogger(__name__)

_RAW_RESPONSE_FILE = "sdb_resp.txt"
_COMMENTS_COL_IDX = 11


class SDB:
    """Class to handle the 4607 Scouting Database requests."""

    def __init__(self) -> None:
        self._session = requests.Session()
        self.url = SCOUTING_DATABASE_URL
        self.filename = SCOUTING_DATABASE_FILENAME
        self.pits_url = PITS_DATABASE_URL
        self.pits_filename = PITS_DATABASE_FILENAME

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def get_full_scouting_database(self, force: bool = False) -> pd.DataFrame:
        """Get the entire 4607 scouting database.

        Args:
            force (bool): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: 4607's scouting database.

        Raises:
            requests.HTTPError: If the server returns a non-2xx response.
        """
        if not force and Path(self.filename).is_file():
            logger.debug("Loading cached scouting database from '%s'.", self.filename)
            return pd.read_csv(self.filename)
        self._fetch_and_cache(url=self.url, filename=self.filename)
        return pd.read_csv(self.filename)

    def get_event_scouting_data(self, event_key: str, force: bool = False) -> pd.DataFrame:
        """Get scouting data for a specific event.

        Filters rows by event_key, drops the unique row ID, and removes duplicates.

        Args:
            event_key (str): The FIRST event key.
            force (bool): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: Scouting data for the given event.
        """
        df = self.get_full_scouting_database(force)
        return df[df["event_key"] == event_key].drop("id", axis=1).drop_duplicates()

    def get_teams_scouting_data(self, teams: list[str], force: bool = False) -> pd.DataFrame:
        """Get scouting data for a list of teams.

        Filters rows by team number, drops the unique row ID, and removes duplicates.

        Args:
            teams (list[str]): List of team numbers to include.
            force (bool): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: Scouting data for the given teams.
        """
        df = self.get_full_scouting_database(force)
        return df[df["team_number"].isin(teams)].drop("id", axis=1).drop_duplicates()

    def get_full_pits_database(self, force: bool = False) -> pd.DataFrame:
        """Get the entire 4607 pits database.

        Args:
            force (bool): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: 4607's pits database.

        Raises:
            requests.HTTPError: If the server returns a non-2xx response.
        """
        if not force and Path(self.pits_filename).is_file():
            logger.debug("Loading cached pits database from '%s'.", self.pits_filename)
            return pd.read_csv(self.pits_filename)
        self._fetch_and_cache(url=self.pits_url, filename=self.pits_filename)
        return pd.read_csv(self.pits_filename)

    def get_event_pits_data(self, event_key: str, force: bool = False) -> pd.DataFrame:
        """Get pits data for a specific event.

        Filters rows by event_key, drops the unique row ID, and removes duplicates.

        Args:
            event_key (str): The FIRST event key.
            force (bool): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: Pits data for the given event.
        """
        df = self.get_full_pits_database(force)
        return df[df["event_key"] == event_key].drop("id", axis=1).drop_duplicates()

    def get_teams_pits_data(self, teams: list[str], force: bool = False) -> pd.DataFrame:
        """Get pits data for a list of teams.

        Filters rows by team number, drops the unique row ID, and removes duplicates.

        Args:
            teams (list[str]): List of team numbers to include.
            force (bool): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: Pits data for the given teams.
        """
        df = self.get_full_pits_database(force)
        return df[df["team_number"].isin(teams)].drop("id", axis=1).drop_duplicates()

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _fetch_and_cache(self, url: str | None = None, filename: str | None = None) -> None:
        """Fetch raw data from the server, parse it, and save to CSV.

        Args:
            url (str): URL to fetch from. Defaults to self.url.
            filename (str): Cache filename. Defaults to self.filename.

        Raises:
            requests.HTTPError: If the server returns a non-2xx response.
        """
        url = url or self.url
        filename = filename or self.filename

        try:
            resp = self._session.get(url=url)
            resp.raise_for_status()
        except requests.HTTPError as e:
            logger.error("HTTP error fetching database from '%s': %s", url, e)
            raise

        raw_text = resp.text
        Path(_RAW_RESPONSE_FILE).write_text(raw_text, encoding="utf-8")
        logger.info("Raw response saved to '%s'.", _RAW_RESPONSE_FILE)

        df = self._parse_csv(raw_text)
        df["scouted_time"] = df["scouted_time"].apply(self._convert_datetime)
        df.to_csv(filename, index=False)
        logger.info("Database cached to '%s'.", filename)

    def _parse_csv(self, raw_text: str, debug: bool = False) -> pd.DataFrame:
        """Parse a potentially malformed CSV response into a DataFrame.

        Handles two known anomalies:
        - Rows split across multiple lines (too few columns).
        - Extra commas inside the comments field (too many columns), resolved
          by joining the overflow tokens at column index _COMMENTS_COL_IDX with '-'.

        Args:
            raw_text (str): Raw CSV text from the server.
            debug (bool): Log extra detail about non-conforming rows. Defaults to False.

        Returns:
            pd.DataFrame: Parsed scouting data.
        """
        db: list[list[str]] = []
        exp_num_cols: int | None = None
        line_continuation = ""

        for line_num, line in enumerate(raw_text.splitlines(), start=1):
            split_line = line.strip().split(",")
            num_cols = len(split_line)

            # First row — capture headers and expected column count
            if line_num == 1:
                exp_num_cols = num_cols
                db.append(split_line)
                continue

            # Happy path
            if num_cols == exp_num_cols:
                if line_continuation:
                    logger.warning("Discarding incomplete continuation before line %d.", line_num)
                    line_continuation = ""
                db.append(split_line)

            # Too few columns — may be a split row
            elif num_cols < exp_num_cols:
                if line_continuation:
                    combined = line_continuation + line.strip()
                    parts = combined.split(",")
                    if len(parts) == exp_num_cols:
                        if debug:
                            logger.debug("Continued line resolved: %s", combined)
                        db.append(parts)
                        line_continuation = ""
                    else:
                        line_continuation = combined
                else:
                    if debug:
                        logger.debug(
                            "Non-conforming CSV (continuation): line=%d, num_cols=%d, exp=%d",
                            line_num,
                            num_cols,
                            exp_num_cols,
                        )
                    line_continuation = line.strip()

            # Too many columns — extra commas in the comments field
            else:
                if debug:
                    logger.debug(
                        "Non-conforming CSV (extra commas): line=%d, num_cols=%d, exp=%d",
                        line_num,
                        num_cols,
                        exp_num_cols,
                    )
                while len(split_line) > exp_num_cols:
                    joined = "-".join([split_line[_COMMENTS_COL_IDX], split_line[_COMMENTS_COL_IDX + 1]])
                    split_line[_COMMENTS_COL_IDX] = joined
                    split_line.pop(_COMMENTS_COL_IDX + 1)
                    if debug:
                        logger.debug("Comments tokens joined: %s", joined)
                db.append(split_line)

        return pd.DataFrame(db[1:], columns=db[0])

    @staticmethod
    def _convert_datetime(in_datetime: str) -> str:
        """Convert a JS-style datetime string to a compact sortable format.

        Input:  'Sat Mar 22 2025 10:40:31 GMT-0500 (Central Daylight Time)'
        Output: '2025-Mar-22 10:40:31'

        Args:
            in_datetime (str): Raw datetime string from the scouting database.

        Returns:
            str: Reformatted datetime string, or the original if the format is unrecognised.
        """
        parts = in_datetime.split()
        if len(parts) != 9:
            logger.warning("Unrecognised datetime format: '%s'", in_datetime)
            return in_datetime
        return f"{parts[3]}-{parts[1]}-{parts[2]} {parts[4]}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch the 4607 scouting database.")
    parser.add_argument("--force", action="store_true", help="Bypass cache and re-fetch from server.")
    args = parser.parse_args()

    sdb = SDB()
    sdb.get_full_scouting_database(force=args.force)
