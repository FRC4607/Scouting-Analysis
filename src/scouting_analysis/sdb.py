"""The 4607 Scouting Database Module"""

from pathlib import Path
import pandas as pd
import requests
from .constants import SCOUTING_DATABASE_URL, SCOUTING_DATABASE_FILENAME


class SDB:
    """Class to handle the 4607 Scouting Database requests"""

    def __init__(self):
        self.url = SCOUTING_DATABASE_URL
        self.filename = SCOUTING_DATABASE_FILENAME

    def __get_scouting_data_from_server(self):
        # Get data from the server
        resp = requests.Session().get(url=self.url)

        # Save the raw text response
        with open("sdb_resp.txt", "w", encoding="utf8") as f:
            f.write(resp.text)

        # Clean up the data and save to JSON/CSV
        with open("sdb_resp.txt", "r", encoding="utf8") as f:
            line_num = 0
            first_row = True
            exp_num_cols = None
            db = []
            line_continuation = ""

            # Process each line
            for line in f.readlines():
                line_num += 1
                split_line = line.strip().split(",")
                num_cols = len(split_line)

                # The first row has the column headers
                if first_row:
                    first_row = False
                    exp_num_cols = len(line.strip().split(","))
                    db.append(split_line)
                    continue

                # If the row has the correct number of columns, it's good-to-go
                if num_cols == exp_num_cols:
                    db.append(split_line)

                # Handle the non-conforming number of columns
                else:
                    if line_continuation:
                        line_continuation += line.strip()
                        split_line_continuation = line_continuation.split(",")
                        if len(split_line_continuation) == exp_num_cols:
                            print(f"  Continued line: {line_continuation}\n")
                            db.append(split_line_continuation)
                            line_continuation = ""
                    else:
                        # Assume lines are continued onto the next line when there aren't enough columns
                        if num_cols < exp_num_cols:
                            print(
                                f"Non-conforming CSV (continuation): line={line_num},\
                                  num_col={num_cols}, exp_num_cols={exp_num_cols}"
                            )
                            line_continuation = line.strip()

                        # Assume the extra commas are in the "comments"
                        else:
                            print(
                                f"Non-conforming CSV (extra commas): line={line_num},\
                                  num_col={num_cols}, exp_num_cols={exp_num_cols}"
                            )
                            comments_idx = 11
                            while num_cols != exp_num_cols:
                                s = "-".join([split_line[comments_idx], split_line[comments_idx + 1]])
                                split_line[comments_idx] = s
                                split_line.pop(comments_idx + 1)
                                num_cols = len(split_line)
                                print(f"  Comments concatenated: {s}\n")
                            db.append(split_line)

        # Save the cleaned up scouting database
        df = pd.DataFrame(db[1:], columns=db[0])
        df.to_csv(self.filename, index=False)

    def get_full_scouting_database(self, force: bool = False) -> pd.DataFrame:
        """Get the whole 4607 scouting database

        Args:
            force (bool, optional): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: 4607's scouting database
        """
        if not force:
            if Path(self.filename).is_file():
                return pd.read_csv(self.filename)
        self.__get_scouting_data_from_server()
        return pd.read_csv(self.filename)

    def get_event_scouting_data(self, event_key: str, force: bool = False) -> pd.DataFrame:
        """Get the 4607 scouting data for an event

        This function will filter out all of the rows matching the input event_key. The unique
        row ID is removed and the duplicate rows are dropped.

        Args:
            event_key (str): The FIRST event key
            force (bool, optional): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: 4607's scouting database
        """
        df = self.get_full_scouting_database(force)
        return df[df["event_key"] == event_key].drop("id", axis=1).drop_duplicates()


if __name__ == "__main__":
    sdb = SDB()
    sdb.get_full_scouting_database(force=True)
