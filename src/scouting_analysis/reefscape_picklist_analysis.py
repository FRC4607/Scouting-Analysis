"""The 2025 Reefscape Picklist Analysis Module"""

import yaml  # pylint: disable=E0401
import pandas as pd


class ReefscapePicklistAnalysis:  # pylint: disable=R0903,R0902
    """Reefscape picklist analysis class"""

    def __init__(self, scouting_df: pd.DataFrame, metric: str, match_breakdowns_df: pd.DataFrame):
        self.scouting_df = scouting_df
        self.metric = metric
        self.match_breakdowns_df = match_breakdowns_df
        self.auto_df = self.__get_auto_team_summary(self.scouting_df)
        self.teleop_coral_df = self.__get_teleop_coral_summary(self.scouting_df)
        self.teleop_algae_df = self.__get_teleop_algae_summary(self.scouting_df)
        self.endgame_df = self.__get_tba_endgame_summary(self.match_breakdowns_df)
        self.comments_df = self.__get_comments_summary(self.scouting_df)
        self.breakdown_df = self.__get_breakdown_summary(self.scouting_df)

    def __get_stats_summary(self, df: pd.DataFrame, col: str) -> pd.DataFrame:
        """Compute statistics for the given column grouped by team

        Args:
            df (pd.DataFrame): Input data
            col (str): The input data column name to comppute statistics on

        Returns:
            pd.DataFrame: Returned statistecs for each team
        """
        group = df.groupby("team_number")
        stats_summary_df = pd.DataFrame(
            [
                group[col].count().rename("n"),
                group[col].mean().rename("mean"),
                group[col].median().rename("median"),
                group[col].std().rename("std"),
                group[col].min().rename("min"),
                group[col].max().rename("max"),
            ]
        ).T.reset_index()
        stats_summary_df.sort_values("mean", inplace=True, ascending=False)
        return stats_summary_df

    def __get_auto_team_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Scouting data autonomous analysis used for generating a picklist

        Columns                 Value
        ---------------------------------------------------------------------------
        mobility                3 points
        Level1                  3 points
        Level2                  4 points
        Level3                  6 points
        Level4                  7 points
        auto_algae              4 or 6 points...assume 4

        Args:
            df (pd.DataFrame): The scouting data

        Returns:
            pd.DataFrame: The autonomous analysis teams summary
        """
        df["mobility_score"] = df["mobility"].apply(lambda x: 3 if x else 0)

        df["total_auto_points"] = (
            df.fillna(0)["mobility_score"]
            + df.fillna(0)["Level1"] * 3
            + df.fillna(0)["Level2"] * 4
            + df.fillna(0)["Level3"] * 6
            + df.fillna(0)["Level4"] * 7
            + df.fillna(0)["auto_algae"] * 4
        )
        teams_summary = self.__get_stats_summary(df, "total_auto_points")
        return teams_summary

    def __get_teleop_coral_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Scouting data teleop analysis used for generating a picklist

        Columns                 Value
        ---------------------------------------------------------------------------
        tele_Level1             2 points
        tele_Level2             3 points
        tele_Level3             4 points
        tele_Level4             5 points
        tele_algae              4 or 6 points...assume 4

        Args:
            df (pd.DataFrame): The scouting data

        Returns:
            pd.DataFrame: The teleop analysis teams summary

        """
        df["total_coral_points"] = (
            df.fillna(0)["tele_Level1"] * 2
            + df.fillna(0)["tele_Level2"] * 3
            + df.fillna(0)["tele_Level3"] * 4
            + df.fillna(0)["tele_Level4"] * 5
        )
        return self.__get_stats_summary(df, "total_coral_points")

    def __get_teleop_algae_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Scouting data teleop analysis used for generating a picklist

        Columns                 Value
        ---------------------------------------------------------------------------
        robo_barge_score        4 points
        processor_scored        2 points (assume other team scores 4)

        Args:
            df (pd.DataFrame): The scouting data

        Returns:
            pd.DataFrame: The teleop analysis teams summary

        """
        df["total_algae_points"] = df.fillna(0)["robo_barge_score"] * 4 + df.fillna(0)["processor_scored"] * 2
        return self.__get_stats_summary(df, "total_algae_points")

    # def __get_sdb_endgame_summary(self, df: pd.DataFrame) -> pd.DataFrame:
    #     """Scouting data endgame analysis used for generating a picklist

    #     Columns                 Value
    #     ---------------------------------------------------------------------------
    #     climb

    #     Args:
    #         df (pd.DataFrame): The scouting data

    #     Returns:
    #         pd.DataFrame: The endgame analysis teams summary
    #     """
    def __get_tba_endgame_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        data = {}
        for _, row in df.iterrows():
            blue_scores = yaml.load(row["score_breakdown"], Loader=yaml.Loader)["blue"]
            for idx, team in enumerate(yaml.load(row["alliances"], Loader=yaml.Loader)["blue"]["team_keys"]):
                team = int(team[3:])
                if team not in data:
                    data[team] = [blue_scores["endGameRobot" + str(idx + 1)]]
                else:
                    data[team].append(blue_scores["endGameRobot" + str(idx + 1)])

            red_scores = yaml.load(row["score_breakdown"], Loader=yaml.Loader)["red"]
            for idx, team in enumerate(yaml.load(row["alliances"], Loader=yaml.Loader)["red"]["team_keys"]):
                team = int(team[3:])
                if team not in data:
                    data[team] = [red_scores["endGameRobot" + str(idx + 1)]]
                else:
                    data[team].append(red_scores["endGameRobot" + str(idx + 1)])
        d = []
        for team, vals in data.items():
            for val in vals:
                d.append([team, val])
        endgame_df = pd.DataFrame(d, columns=["team_number", "climb"])

        endgame_df["climb_score"] = endgame_df["climb"].apply(
            lambda x: 12 if x == "DeepCage" else 6 if x == "ShallowCage" else 2 if x == "Parked" else 0
        )
        return self.__get_stats_summary(endgame_df, "climb_score")

    def __get_breakdown_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Scouting data endgame analysis used for generating a picklist

        Columns                 Value
        ---------------------------------------------------------------------------
        breakdown

        Args:
            df (pd.DataFrame): The scouting data

        Returns:
            pd.DataFrame: The breakdown analysis teams summary
        """
        df["breakdown"] = df.fillna(0)["breakdown"].apply(lambda x: 1 if x else 0)
        group = df.groupby("team_number")["breakdown"]
        breakdown_summary_df = pd.DataFrame(
            [
                group.sum(),
            ]
        ).T.reset_index()
        return breakdown_summary_df

    def __get_comments_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Summarize all scouter commeents

        Columns                 Value
        ---------------------------------------------------------------------------
        scouter_name            Track scouter for further questions
        comments                This will track the hard-to-quantify things

        Args:
            df (pd.DataFrame): The scouting data

        Returns:
            pd.DataFrame: The comments teams summary
        """
        df["comments"] = df["comments"].fillna("")
        group = df.groupby("team_number")
        summary_df = pd.DataFrame(
            [group["comments"].aggregate(lambda x: " | ".join(x))]  # pylint: disable=W0108
        ).T.reset_index()
        return summary_df

    def get_picklist_summary(
        self, auto_weight: int, coral_weight: int, algae_weight: int, endgame_weight: int
    ) -> pd.DataFrame:
        """Summarize the auto, telop, endgame, and comment data into the final picklist"""
        auto_picklist = pd.DataFrame(
            [
                self.auto_df["team_number"],
                (
                    (self.auto_df[self.metric].rename(f"auto_norm_{self.metric}") - self.auto_df[self.metric].min())
                    / (self.auto_df[self.metric].max() - self.auto_df[self.metric].min())
                    * auto_weight
                ),
                self.auto_df["n"],
            ]
        ).T

        teleop_coral_picklist = pd.DataFrame(
            [
                self.teleop_coral_df["team_number"],
                (
                    (
                        self.teleop_coral_df[self.metric].rename(f"teleop_coral_norm_{self.metric}")
                        - self.teleop_coral_df[self.metric].min()
                    )
                    / (self.teleop_coral_df[self.metric].max() - self.teleop_coral_df[self.metric].min())
                    * coral_weight
                ),
            ]
        ).T

        teleop_algae_picklist = pd.DataFrame(
            [
                self.teleop_algae_df["team_number"],
                (
                    (
                        self.teleop_algae_df[self.metric].rename(f"teleop_algae_norm_{self.metric}")
                        - self.teleop_algae_df[self.metric].min()
                    )
                    / (self.teleop_algae_df[self.metric].max() - self.teleop_algae_df[self.metric].min())
                    * algae_weight
                ),
            ]
        ).T

        endgame_picklist = pd.DataFrame(
            [
                self.endgame_df["team_number"],
                (
                    (
                        self.endgame_df[self.metric].rename(f"endgame_norm_{self.metric}")
                        - self.endgame_df[self.metric].min()
                    )
                    / (self.endgame_df[self.metric].max() - self.endgame_df[self.metric].min())
                    * endgame_weight
                ),
            ]
        ).T

        breakdown_picklist = pd.DataFrame(
            [
                self.breakdown_df["team_number"],
                self.breakdown_df["breakdown"],
            ]
        ).T

        comments_picklist = pd.DataFrame(
            [
                self.comments_df["team_number"],
                self.comments_df["comments"],
            ]
        ).T

        picklist_df = pd.merge(auto_picklist, teleop_coral_picklist, on="team_number")
        picklist_df = pd.merge(picklist_df, teleop_algae_picklist, on="team_number")
        picklist_df = pd.merge(picklist_df, endgame_picklist, on="team_number")
        picklist_df = pd.merge(picklist_df, breakdown_picklist, on="team_number")
        picklist_df = pd.merge(picklist_df, comments_picklist, on="team_number")
        picklist_df = picklist_df[
            [
                "team_number",
                f"auto_norm_{self.metric}",
                f"teleop_coral_norm_{self.metric}",
                f"teleop_algae_norm_{self.metric}",
                f"endgame_norm_{self.metric}",
                "n",
                "breakdown",
                "comments",
            ]
        ]

        picklist_df["team_number"] = picklist_df["team_number"].astype(int)
        picklist_df["n"] = picklist_df["n"].astype(int)

        picklist_score = (
            picklist_df[f"auto_norm_{self.metric}"]
            + picklist_df[f"teleop_coral_norm_{self.metric}"]
            + picklist_df[f"teleop_algae_norm_{self.metric}"]
            + picklist_df[f"endgame_norm_{self.metric}"]
        )
        picklist_df.insert(1, "score", picklist_score)
        picklist_df.sort_values("score", inplace=True, ascending=False)

        picklist_df.rename(
            columns={
                "team_number": "team",
                f"auto_norm_{self.metric}": "auto",
                f"teleop_coral_norm_{self.metric}": "teleop coral",
                f"teleop_algae_norm_{self.metric}": "teleop algae",
                f"endgame_norm_{self.metric}": "endgame",
            },
            inplace=True,
        )

        return picklist_df

    def get_picklist_summary2(self) -> pd.DataFrame:
        """Summarize the auto, telop, endgame, and comment data into the final picklist"""
        auto_picklist = pd.DataFrame(
            [
                self.auto_df["team_number"],
                ((self.auto_df[self.metric].rename(f"auto_norm_{self.metric}"))),
                self.auto_df["n"],
            ]
        ).T
        teleop_coral_picklist = pd.DataFrame(
            [
                self.teleop_coral_df["team_number"],
                ((self.teleop_coral_df[self.metric].rename(f"teleop_coral_norm_{self.metric}"))),
            ]
        ).T

        teleop_algae_picklist = pd.DataFrame(
            [
                self.teleop_algae_df["team_number"],
                ((self.teleop_algae_df[self.metric].rename(f"teleop_algae_norm_{self.metric}"))),
            ]
        ).T

        endgame_picklist = pd.DataFrame(
            [
                self.endgame_df["team_number"],
                ((self.endgame_df[self.metric].rename(f"endgame_norm_{self.metric}"))),
            ]
        ).T

        breakdown_picklist = pd.DataFrame(
            [
                self.breakdown_df["team_number"],
                self.breakdown_df["breakdown"],
            ]
        ).T

        comments_picklist = pd.DataFrame(
            [
                self.comments_df["team_number"],
                self.comments_df["comments"],
            ]
        ).T

        picklist_df = pd.merge(auto_picklist, teleop_coral_picklist, on="team_number")
        picklist_df = pd.merge(picklist_df, teleop_algae_picklist, on="team_number")
        picklist_df = pd.merge(picklist_df, endgame_picklist, on="team_number")
        picklist_df = pd.merge(picklist_df, breakdown_picklist, on="team_number")
        picklist_df = pd.merge(picklist_df, comments_picklist, on="team_number")
        picklist_df = picklist_df[
            [
                "team_number",
                f"auto_norm_{self.metric}",
                f"teleop_coral_norm_{self.metric}",
                f"teleop_algae_norm_{self.metric}",
                f"endgame_norm_{self.metric}",
                "n",
                "breakdown",
                "comments",
            ]
        ]

        picklist_df["team_number"] = picklist_df["team_number"].astype(int)
        picklist_df["n"] = picklist_df["n"].astype(int)

        picklist_score = (
            picklist_df[f"auto_norm_{self.metric}"]
            + picklist_df[f"teleop_coral_norm_{self.metric}"]
            + picklist_df[f"teleop_algae_norm_{self.metric}"]
            + picklist_df[f"endgame_norm_{self.metric}"]
        )
        picklist_df.insert(1, "score", picklist_score)
        picklist_df.sort_values("score", inplace=True, ascending=False)

        picklist_df.rename(
            columns={
                "team_number": "team",
                f"auto_norm_{self.metric}": "auto",
                f"teleop_coral_norm_{self.metric}": "teleop coral",
                f"teleop_algae_norm_{self.metric}": "teleop algae",
                f"endgame_norm_{self.metric}": "endgame",
            },
            inplace=True,
        )

        return picklist_df
