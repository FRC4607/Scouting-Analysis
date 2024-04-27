""" The 4607 Scouting Database Module
"""

from pathlib import Path
import pandas as pd
import requests
from .constants import SCOUTING_DATABASE_URL


class SDB:
    """Class to handle the 4607 Scouting Database requests"""

    def __init__(self):
        self.url = SCOUTING_DATABASE_URL

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
            for line in f.readlines():
                line_num += 1
                split_line = line.strip().split(",")
                num_cols = len(split_line)
                if first_row:
                    first_row = False
                    exp_num_cols = len(line.strip().split(","))
                    db.append(split_line)
                    continue
                if num_cols == exp_num_cols:
                    db.append(split_line)
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
                        # Assume the extra commas are in the comments
                        else:
                            print(
                                f"Non-conforming CSV (extra commas): line={line_num},\
                                num_col={num_cols}, exp_num_cols={exp_num_cols}"
                            )
                            while num_cols != exp_num_cols:
                                split_line[-3] += split_line[-2]
                                split_line.pop(-2)
                                num_cols = len(split_line)
                                s = ",".join(split_line)
                                print(f"  Comments concatenated: {s}\n")

        df = pd.DataFrame(db[1:], columns=db[0])
        df.to_csv("full_scouting_database.csv", index=False)

    def get_scouting_data(self, force: bool = False) -> pd.DataFrame:
        """Get the whole 4607 scouting database

        Args:
            force (bool, optional): Skip cached data and force a refresh. Defaults to False.

        Returns:
            pd.DataFrame: 4607's scouting database
        """
        filename = "full_scouting_database.csv"
        if not force:
            if Path(filename).is_file():
                return pd.read_csv(filename)
        self.__get_scouting_data_from_server()
        return pd.read_csv(filename)
