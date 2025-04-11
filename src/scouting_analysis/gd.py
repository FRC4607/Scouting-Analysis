"""The 4607 Google Drive Module"""

import pandas as pd
import pygsheets
from .constants import (
    GOOGLE_SERVICE_FILE,
    GOOGLE_SHARED_DRIVE_ID,
    GOOGLE_PICKLIST_SUMMARY,
    GOOGLE_MATCH_PLANNING_SUMMARY,
)


class GD:
    """Class to handle Google Drive spreadsheets"""

    def __init__(self, workspace: str):
        client = pygsheets.authorize(service_file=workspace + "\\" + GOOGLE_SERVICE_FILE)
        client.drive.enable_team_drive(GOOGLE_SHARED_DRIVE_ID)
        self.pl = client.open(GOOGLE_PICKLIST_SUMMARY)
        self.mp = client.open(GOOGLE_MATCH_PLANNING_SUMMARY)

    def save_picklist_to_google_drive(self, df: pd.DataFrame, sheet_name: str):
        """Save scouting data to a shared Google Drive spreadsheet

        Args:
            df (pd.DataFrame): The dataframe
            sheet_name (str): The sheet name to save the dataframe to (will overwrite if the sheet already exists!)
        """
        # Create the worksheet
        sheets = [i.title for i in self.pl.worksheets()]
        if sheet_name in sheets:
            self.pl.del_worksheet(self.pl.worksheet_by_title(sheet_name))
        self.pl.add_worksheet(sheet_name, src_worksheet=self.pl.worksheet_by_title("Template"), index=0)
        active_sheet = self.pl.worksheet_by_title(sheet_name)
        active_sheet.set_dataframe(df, "A1")

    def save_match_planning_to_google_drive(self, df: pd.DataFrame, sheet_name: str):
        """Save scouting match planning data to a shared Google Drive spreadsheet

        Args:
            df (pd.DataFrame): The dataframe
            sheet_name (str): The sheet name to save the dataframe to (will overwrite if the sheet already exists!)
        """
        # Create the worksheet
        sheets = [i.title for i in self.mp.worksheets()]
        if sheet_name in sheets:
            self.mp.del_worksheet(self.mp.worksheet_by_title(sheet_name))
        self.mp.add_worksheet(sheet_name, src_worksheet=self.mp.worksheet_by_title("Template"), index=0)
        active_sheet = self.mp.worksheet_by_title(sheet_name)
        active_sheet.set_dataframe(df, "A1")

    def get_picklist_from_google_drive(self, sheet_name: str) -> pd.DataFrame:
        """Get the picklist from the shared Google Drive spreadsheet

        Args:
            sheet_name (str): The sheet name to get the picklist from

        Returns:
            pd.DataFrame: The picklist
        """
        active_sheet = self.pl.worksheet_by_title(sheet_name)
        return active_sheet.get_as_df()
