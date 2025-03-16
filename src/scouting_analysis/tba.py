"""The Blue Alliance API Module"""

from io import StringIO
from pathlib import Path
import requests
import pandas as pd
from .constants import TBA_BASE


class TBA:
    """Class to handle The Blue Alliance data requests

    Args:
        tba_api_key (str): A personal key to access the blue alliance API
    """

    def __init__(self, tba_api_key: str):
        self.headers = {"X-TBA-Auth-Key": tba_api_key}

    def __make_request(self, url: str) -> pd.DataFrame:
        resp = requests.Session().get(url=url, headers=self.headers)
        return pd.read_json(StringIO(resp.text))

    def __request_event_teams_data(self, event_key: str) -> pd.DataFrame:
        url = TBA_BASE + "/event/" + event_key + "/teams"
        return self.__make_request(url)

    def __request_team_events_data(self, team_key: str) -> pd.DataFrame:
        url = TBA_BASE + "/team/" + team_key + "/events"
        return self.__make_request(url)

    def __request_event_match_breakdown_data(self, event_key: str) -> pd.DataFrame:
        url = TBA_BASE + "/event/" + event_key + "/matches"
        return self.__make_request(url)

    def get_event_team_list(self, event_key: str, force: bool = False) -> pd.DataFrame:
        """Get team list for an event

        Args:
            event_key (str): The event key - see https://frc-events.firstinspires.org/2024/Events/EventList
            force (bool, optional): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: The list of teams registered for the event
        """
        filename = f"event_data_{event_key}.csv"
        if not force:
            if Path(filename).is_file():
                return pd.read_csv(filename)
        self.__request_event_teams_data(event_key).to_csv(filename, index=False)  # pylint: disable=E1101
        return pd.read_csv(filename)

    def get_team_event_list(self, team_key: str, force: bool = False) -> pd.DataFrame:
        """Get event list for a team

        Args:
            team_key (str): The team key
            force (bool, optional): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: The list of events the team has competed in
        """
        filename = f"team_data_{team_key}.csv"
        if not force:
            if Path(filename).is_file():
                return pd.read_csv(filename)
        self.__request_team_events_data(team_key).to_csv(filename, index=False)  # pylint: disable=E1101
        return pd.read_csv(filename)

    def get_event_match_breakdowns(self, event_key: str, force: bool = False) -> pd.DataFrame:
        """Get match breakdowns for the given event

        Args:
            event_key (str): The event key - see https://frc-events.firstinspires.org/2024/Events/EventList
            force (bool, optional): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: The list of teams registered for the event
        """
        filename = f"match_breakdowns_{event_key}.csv"
        if not force:
            if Path(filename).is_file():
                return pd.read_csv(filename)
        self.__request_event_match_breakdown_data(event_key).to_csv(filename, index=False)  # pylint: disable=E1101
        return pd.read_csv(filename)
