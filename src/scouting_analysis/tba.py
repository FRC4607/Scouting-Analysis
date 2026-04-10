"""The Blue Alliance API Module"""

import logging
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

from .constants import TBA_BASE

logger = logging.getLogger(__name__)


class TBA:
    """Class to handle The Blue Alliance data requests.

    Args:
        tba_api_key (str): A personal key to access the Blue Alliance API.
    """

    def __init__(self, tba_api_key: str) -> None:
        self._session = requests.Session()
        self._headers = {"X-TBA-Auth-Key": tba_api_key}

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def get_event_team_list(self, event_key: str, force: bool = False) -> pd.DataFrame:
        """Get the team list for an event.

        Args:
            event_key (str): The event key - see https://frc-events.firstinspires.org/2024/Events/EventList
            force (bool): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: The list of teams registered for the event.
        """
        return self._get_cached(
            filename=f"event_data_{event_key}.csv",
            endpoint=f"/event/{event_key}/teams",
            force=force,
        )

    def get_team_event_list(self, team_key: str, force: bool = False) -> pd.DataFrame:
        """Get the event list for a team.

        Args:
            team_key (str): The team key (e.g. 'frc4607').
            force (bool): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: The list of events the team has competed in.
        """
        return self._get_cached(
            filename=f"team_data_{team_key}.csv",
            endpoint=f"/team/{team_key}/events",
            force=force,
        )

    def get_event_match_breakdowns(self, event_key: str, force: bool = False) -> pd.DataFrame:
        """Get full match breakdowns for an event.

        Args:
            event_key (str): The event key - see https://frc-events.firstinspires.org/2024/Events/EventList
            force (bool): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: Match breakdown data for the event.
        """
        return self._get_cached(
            filename=f"match_breakdowns_{event_key}.csv",
            endpoint=f"/event/{event_key}/matches",
            force=force,
        )

    def get_event_matches(self, event_key: str, force: bool = False) -> pd.DataFrame:
        """Get the match schedule for team frc4607 at an event.

        Args:
            event_key (str): The event key - see https://frc-events.firstinspires.org/2024/Events/EventList
            force (bool): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: Simplified match schedule for frc4607 at the event.
        """
        return self._get_cached(
            filename=f"event_matches_{event_key}.csv",  # BUG FIX: was sharing filename with match_breakdowns
            endpoint=f"/team/frc4607/event/{event_key}/matches/simple",
            force=force,
        )

    def get_event_coprs(self, event_key: str, force: bool = False) -> pd.DataFrame:
        """Get Component OPR (COPR) data for all teams at an event.

        Args:
            event_key (str): The event key - see https://frc-events.firstinspires.org/2024/Events/EventList
            force (bool): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: COPR data keyed by team number.
        """
        filename = f"event_coprs_{event_key}.csv"
        if not force and Path(filename).is_file():
            logger.debug("Loading cached COPRs from '%s'.", filename)
            return pd.read_csv(filename, index_col=0)

        df = self._make_request(f"/event/{event_key}/coprs")
        df.to_csv(filename, index=True)
        logger.info("Fetched and cached '%s'.", filename)
        return df

    def get_event_oprs(self, event_key: str, force: bool = False) -> pd.DataFrame:
        """Get OPR, DPR, and CCWM for all teams at an event.

        Args:
            event_key (str): The event key.
            force (bool): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: OPR, DPR, and CCWM keyed by team number.
        """
        filename = f"event_oprs_{event_key}.csv"
        if not force and Path(filename).is_file():
            logger.debug("Loading cached OPRs from '%s'.", filename)
            return pd.read_csv(filename, index_col="team_key")

        df = self._make_request(f"/event/{event_key}/oprs")
        df.index.name = "team_key"
        df.to_csv(filename, index=True)
        logger.info("Fetched and cached '%s'.", filename)
        return df

    def get_prior_event_coprs(self, event_key: str, year: int) -> pd.DataFrame:
        """Build a COPR DataFrame using each team's most recent prior-event COPRs.

        For each team at *event_key*, finds the most recent event they played
        before the current one, fetches that event's COPRs, and assembles a
        combined DataFrame in the same format as get_event_coprs().

        Prior-event data is historical and never force-refreshed.

        Args:
            event_key (str): The current event key.
            year (int): The competition year.

        Returns:
            pd.DataFrame: COPR data indexed by team key (e.g. 'frc4607').
                          Empty if no prior-event data is available.
        """
        current_start = self._get_event_start_date(event_key)
        if not current_start:
            return pd.DataFrame()

        teams_df = self.get_event_team_list(event_key, force=False)
        if teams_df.empty or "team_number" not in teams_df.columns:
            return pd.DataFrame()

        # Map each team to their most recent prior event
        team_prior: dict[str, str] = {}
        for team_num in teams_df["team_number"]:
            team_key = f"frc{int(team_num)}"
            events_df = self._get_cached(
                filename=f"team_events_{team_key}_{year}.csv",
                endpoint=f"/team/{team_key}/events/{year}/simple",
                force=False,
            )
            if events_df.empty or "start_date" not in events_df.columns or "key" not in events_df.columns:
                continue
            prior = events_df[events_df["start_date"] < current_start]
            if prior.empty:
                continue
            team_prior[team_key] = prior.loc[prior["start_date"].idxmax(), "key"]

        if not team_prior:
            return pd.DataFrame()

        # Fetch COPRs once per unique prior event, then extract each team's row
        event_coprs_cache: dict[str, pd.DataFrame] = {}
        rows: dict[str, dict] = {}
        for team_key, prior_event_key in team_prior.items():
            if prior_event_key not in event_coprs_cache:
                try:
                    event_coprs_cache[prior_event_key] = self.get_event_coprs(prior_event_key, force=False)
                except Exception:
                    event_coprs_cache[prior_event_key] = pd.DataFrame()
            coprs = event_coprs_cache[prior_event_key]
            if not coprs.empty and team_key in coprs.index:
                rows[team_key] = coprs.loc[team_key].to_dict()

        if not rows:
            return pd.DataFrame()

        result = pd.DataFrame.from_dict(rows, orient="index")
        result.index.name = "team_key"
        logger.info("Built prior-event COPRs for %d/%d teams.", len(rows), len(teams_df))
        return result

    # ------------------------------------------------------------------ #
    # Private helpers                                                    #
    # ------------------------------------------------------------------ #

    def _get_event_start_date(self, event_key: str) -> str:
        """Return the start_date string for an event, fetching from TBA if needed.

        Args:
            event_key (str): The event key.

        Returns:
            str: ISO date string (e.g. '2026-03-15'), or '' on failure.
        """
        filename = f"event_simple_{event_key}.csv"
        path = Path(filename)
        if path.is_file():
            df = pd.read_csv(path)
            return str(df.loc[0, "start_date"]) if "start_date" in df.columns else ""

        url = TBA_BASE + f"/event/{event_key}/simple"
        try:
            resp = self._session.get(url=url, headers=self._headers)
            resp.raise_for_status()
            data = resp.json()
            pd.DataFrame([data]).to_csv(path, index=False)
            return str(data.get("start_date", ""))
        except Exception as e:
            logger.error("Failed to fetch event info for '%s': %s", event_key, e)
            return ""

    def _get_cached(self, filename: str, endpoint: str, force: bool) -> pd.DataFrame:
        """Return cached CSV data if available, otherwise fetch from TBA and cache it.

        Args:
            filename (str): Local CSV cache filename.
            endpoint (str): TBA API endpoint path (appended to TBA_BASE).
            force (bool): If True, bypass the cache and re-fetch.

        Returns:
            pd.DataFrame: The requested data.

        Raises:
            requests.HTTPError: If the API returns a non-2xx status code.
            ValueError: If the response cannot be parsed as JSON.
        """
        path = Path(filename)
        if not force and path.is_file():
            logger.debug("Loading cached data from '%s'.", filename)
            return pd.read_csv(path)

        df = self._make_request(endpoint)
        df.to_csv(path, index=False)
        logger.info("Fetched and cached '%s'.", filename)
        return df

    def _make_request(self, endpoint: str) -> pd.DataFrame:
        """Make a GET request to the TBA API and return the result as a DataFrame.

        Args:
            endpoint (str): API endpoint path (appended to TBA_BASE).

        Returns:
            pd.DataFrame: Parsed JSON response.

        Raises:
            requests.HTTPError: If the API returns a non-2xx status code.
            ValueError: If the response body is not valid JSON.
        """
        url = TBA_BASE + endpoint
        try:
            resp = self._session.get(url=url, headers=self._headers)
            resp.raise_for_status()
            return pd.read_json(StringIO(resp.text))
        except requests.HTTPError as e:
            logger.error("HTTP error fetching '%s': %s", url, e)
            raise
        except ValueError as e:
            logger.error("Failed to parse response from '%s': %s", url, e)
            raise


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Fetch TBA event team list.")
    parser.add_argument("event_key", type=str, help="The event key (e.g. '2026ndgf')")
    args = parser.parse_args()

    tba = TBA(tba_api_key=os.environ["X-TBA-Auth-Key"])
    tba.get_event_team_list(event_key=args.event_key)
    tba.get_event_match_breakdowns(event_key=args.event_key)
