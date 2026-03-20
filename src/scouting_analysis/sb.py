"""The Statbotics API Module"""

import logging
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)


class SB:
    """Class to handle Statbotics data requests."""

    def __init__(self) -> None:
        self._session = requests.Session()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def get_event_team_stats(self, event_key: str, force: bool = False) -> pd.DataFrame:
        """Get Statbotics EPA stats for all teams at an event.

        Args:
            event_key (str): The FIRST FRC event key (e.g. '2026ndgf').
            force (bool): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: EPA stats for each team at the event, with columns:
                team_number, auto_epa, teleop_epa, endgame_epa, total_epa.

        Raises:
            requests.HTTPError: If the API returns a non-2xx response.
        """
        filename = f"sb_event_{event_key}.csv"
        if not force and Path(filename).is_file():
            logger.debug("Loading cached Statbotics data from '%s'.", filename)
            return pd.read_csv(filename)

        try:
            resp = self._session.get(f"https://api.statbotics.io/v3/team_events?event={event_key}&limit=100")
            resp.raise_for_status()
            data = resp.json()
        except requests.HTTPError as e:
            print(f"Statbotics unavailable for event '{event_key}': {e} — continuing without EPA data.")
            return pd.DataFrame()

        if not data:
            logger.warning("No Statbotics data found for event '%s'.", event_key)
            return pd.DataFrame()

        records = []
        for entry in data:
            breakdown = entry.get("epa", {}).get("breakdown", {})
            records.append(
                {
                    "team_number": entry["team"],
                    "auto_epa": breakdown.get("auto_points", 0),
                    "teleop_epa": breakdown.get("teleop_points", 0),
                    "endgame_epa": breakdown.get("endgame_points", 0),
                    "total_epa": breakdown.get("total_points", 0),
                }
            )

        df = pd.DataFrame(records)
        df.to_csv(filename, index=False)
        logger.info("Statbotics data cached to '%s'.", filename)
        return df


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch Statbotics EPA stats for an event.")
    parser.add_argument("event_key", type=str, help="The FIRST FRC event key (e.g. '2026ndgf')")
    parser.add_argument("--force", action="store_true", help="Bypass cache and re-fetch.")
    args = parser.parse_args()

    sb = SB()
    print(sb.get_event_team_stats(event_key=args.event_key, force=args.force))
