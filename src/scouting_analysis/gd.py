""" The 4607 Google Drive Module
"""

import pandas as pd
import pygsheets
from .constants import (
    GOOGLE_SERVICE_FILE,
    GOOGLE_SHARED_DRIVE_ID,
    GOOGLE_PICKLIST_SUMMARY,
)


class GD:
    """Class to handle Google Drive spreadsheets"""

    def __init__(self):
        client = pygsheets.authorize(service_file=GOOGLE_SERVICE_FILE)
        client.drive.enable_team_drive(GOOGLE_SHARED_DRIVE_ID)
        self.ss = client.open(GOOGLE_PICKLIST_SUMMARY)

    def save_picklist_to_google_drive(self, df: pd.DataFrame, sheet_name: str):
        """Save scouting data to a shared Google Drive spreadsheet

        Args:
            df (pd.DataFrame): The dataframe
            sheet_name (str): The sheet name to save the dataframe to (will overwrite if the sheet already exists!)
        """
        # Create the worksheet
        sheets = [i.title for i in self.ss.worksheets()]
        if sheet_name in sheets:
            self.ss.del_worksheet(self.ss.worksheet_by_title(sheet_name))
        self.ss.add_worksheet(sheet_name, src_worksheet=self.ss.worksheet_by_title("Template"), index=0)
        active_sheet = self.ss.worksheet_by_title(sheet_name)
        active_sheet.set_dataframe(df, "A1")

    def get_picklist_from_google_drive(self, sheet_name: str) -> pd.DataFrame:
        """Get the picklist from the shared Google Drive spreadsheet

        Args:
            sheet_name (str): The sheet name to get the picklist from

        Returns:
            pd.DataFrame: The picklist
        """
        active_sheet = self.ss.worksheet_by_title(sheet_name)
        return active_sheet.get_as_df()
