"""The 4607 Google Drive Module"""

import logging

import pandas as pd
import pygsheets
from pygsheets import Spreadsheet

from .constants import (
    GOOGLE_MATCH_PLANNING_SUMMARY,
    GOOGLE_PICKLIST_SUMMARY,
    GOOGLE_SERVICE_FILE,
    GOOGLE_SHARED_DRIVE_ID,
)

logger = logging.getLogger(__name__)


class GD:
    """Class to handle Google Drive spreadsheets."""

    def __init__(self, workspace: str) -> None:
        """Initialize the Google Drive client and open target spreadsheets.

        Args:
            workspace (str): Path to the directory containing the service account file.

        Raises:
            FileNotFoundError: If the service account file cannot be found.
            pygsheets.AuthenticationError: If authorization fails.
        """
        try:
            client = pygsheets.authorize(service_file=f"{workspace}\\{GOOGLE_SERVICE_FILE}")
            client.drive.enable_team_drive(GOOGLE_SHARED_DRIVE_ID)
            self.pl = client.open(GOOGLE_PICKLIST_SUMMARY)
            self.mp = client.open(GOOGLE_MATCH_PLANNING_SUMMARY)
        except FileNotFoundError:
            logger.error("Service account file not found in workspace: %s", workspace)
            raise
        except Exception as e:
            logger.error("Failed to initialize Google Drive client: %s", e)
            raise

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def save_picklist_to_google_drive(self, df: pd.DataFrame, sheet_name: str) -> None:
        """Save scouting data to the picklist Google Drive spreadsheet.

        Args:
            df (pd.DataFrame): The dataframe to save.
            sheet_name (str): Destination sheet name (overwritten if it already exists).
        """
        self._save_to_spreadsheet(self.pl, df, sheet_name)

    def save_match_planning_to_google_drive(self, df: pd.DataFrame, sheet_name: str) -> None:
        """Save match planning data to the match planning Google Drive spreadsheet.

        Args:
            df (pd.DataFrame): The dataframe to save.
            sheet_name (str): Destination sheet name (overwritten if it already exists).
        """
        self._save_to_spreadsheet(self.mp, df, sheet_name)

    def get_picklist_from_google_drive(self, sheet_name: str) -> pd.DataFrame:
        """Retrieve a picklist sheet as a DataFrame.

        Args:
            sheet_name (str): The sheet to retrieve.

        Returns:
            pd.DataFrame: The sheet contents.

        Raises:
            pygsheets.WorksheetNotFound: If the sheet does not exist.
        """
        return self._get_from_spreadsheet(self.pl, sheet_name)

    # ------------------------------------------------------------------ #
    # Private helpers                                                    #
    # ------------------------------------------------------------------ #

    def _save_to_spreadsheet(self, spreadsheet: Spreadsheet, df: pd.DataFrame, sheet_name: str) -> None:
        """Create (or replace) a worksheet and write a DataFrame to it.

        Args:
            spreadsheet (Spreadsheet): Target pygsheets Spreadsheet object.
            df (pd.DataFrame): The dataframe to write.
            sheet_name (str): The worksheet name to write to.

        Raises:
            pygsheets.SpreadsheetNotFound: If the spreadsheet cannot be accessed.
            Exception: For any other unexpected Google API errors.
        """
        try:
            existing = {ws.title for ws in spreadsheet.worksheets()}
            if sheet_name in existing:
                spreadsheet.del_worksheet(spreadsheet.worksheet_by_title(sheet_name))

            template = spreadsheet.worksheet_by_title("Template")
            spreadsheet.add_worksheet(sheet_name, src_worksheet=template, index=0)

            active_sheet = spreadsheet.worksheet_by_title(sheet_name)
            active_sheet.set_dataframe(df, "A1")
            logger.info("Saved sheet '%s' to '%s'.", sheet_name, spreadsheet.title)
        except pygsheets.WorksheetNotFound:
            logger.error("'Template' sheet missing in '%s'.", spreadsheet.title)
            raise
        except Exception as e:
            logger.error("Failed to save sheet '%s': %s", sheet_name, e)
            raise

    def _get_from_spreadsheet(self, spreadsheet: Spreadsheet, sheet_name: str) -> pd.DataFrame:
        """Retrieve a worksheet as a DataFrame.

        Args:
            spreadsheet (Spreadsheet): Source pygsheets Spreadsheet object.
            sheet_name (str): The worksheet name to read.

        Returns:
            pd.DataFrame: Contents of the worksheet.

        Raises:
            pygsheets.WorksheetNotFound: If the sheet does not exist.
        """
        try:
            active_sheet = spreadsheet.worksheet_by_title(sheet_name)
            return active_sheet.get_as_df()
        except pygsheets.WorksheetNotFound:
            logger.error("Sheet '%s' not found in '%s'.", sheet_name, spreadsheet.title)
            raise
