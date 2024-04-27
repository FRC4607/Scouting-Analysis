""" The 2024 Crescendo Picklist Analysis Module
"""

import pandas as pd


class CrescendoPicklistAnalysis:
    """Crescendo picklist analysis class"""

    def __init__(self, scouting_df: pd.DataFrame, metric: str):
        self.scouting_df = scouting_df
        self.metric = metric
        self.auto_df = self.__get_auto_team_summary(self.scouting_df)
        self.teleop_df = self.__get_teleop_summary(self.scouting_df)
        self.endgame_df = self.__get_endgame_summary(self.scouting_df)
        self.comments_df = self.__get_comments_summary(self.scouting_df)

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
        mobility                2 points
        auto_amp                2 points
        zone1_shot_made_auto    5 points
        zone2_shot_made_auto    5 points
        pre_load_score          Used to find a good 3rd robot
        starting_pos            Used to find compatible partners
        zone1_shot_miss_auto
        zone2_shot_miss_auto

        Args:
            df (pd.DataFrame): The scouting data

        Returns:
            pd.DataFrame: The autonomous analysis teams summary
        """
        df["mobility"] = df["mobility"].replace({True: 2, False: 0})
        df["pre_load_score"] = df.fillna(0)["pre_load_score"].replace(
            {True: 1, False: 0}
        )

        df["total_auto_points"] = (
            df.fillna(0)["mobility"]
            + df.fillna(0)["auto_amp"] * 2
            + df.fillna(0)["zone1_shot_made_auto"] * 5
            + df.fillna(0)["zone2_shot_made_auto"] * 5
        )
        teams_summary = self.__get_stats_summary(df, "total_auto_points")

        teams_summary = pd.merge(
            teams_summary,
            pd.DataFrame(
                (
                    100
                    * df.groupby("team_number")["pre_load_score"].sum()
                    / df.groupby("team_number")["pre_load_score"].count()
                ).rename("preload%")
            ).reset_index(),
            on="team_number",
        )

        teams_summary = pd.merge(
            teams_summary,
            pd.DataFrame(
                (df.groupby("team_number")["pass_note"].sum()).rename("total_passes")
            ).reset_index(),
            on="team_number",
        )
        return teams_summary

    def __get_teleop_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Scouting data teleop analysis used for generating a picklist

        Since the amp/speaker scoring changes depending on amplification, track the
        number of game pieces instead of the point values.

        Columns                 Value
        ---------------------------------------------------------------------------
        teleop_amp              1 game piece
        zone1_shot_made         1 game piece
        zone2_shot_made         1 game piece
        zone3_shot_made         1 game piece
        zone4_shot_made         1 game piece
        zone1_shot_miss
        zone2_shot_miss
        zone3_shot_miss
        zone4_shot_miss
        # TODO: Amp miss?

        Args:
            df (pd.DataFrame): The scouting data

        Returns:
            pd.DataFrame: The teleop analysis teams summary
        """
        df["teleop_speaker_made"] = (
            df.fillna(0)["zone1_shot_made"] + df.fillna(0)["zone2_shot_made"]
        )

        df["total_teleop_pieces_made"] = (
            df.fillna(0)["teleop_amp"] + df.fillna(0)["teleop_speaker_made"]
        )

        df["total_teleop_pieces_miss"] = (
            df.fillna(0)["zone1_shot_miss"] + df.fillna(0)["zone2_shot_miss"]
        )

        df["total_teleop_pieces_attempted"] = (
            df["total_teleop_pieces_made"] + df["total_teleop_pieces_miss"]
        )
        return self.__get_stats_summary(df, "total_teleop_pieces_made")

    def __get_endgame_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Scouting data endgame analysis used for generating a picklist

        Columns                 Value
        ---------------------------------------------------------------------------
        trap_note_pos_amp       5 points
        trap_note_pos_source    5 points
        trap_note_pos_center    5 points
        rob_onstage             3
        parked                  1
        harmony                 2
        climb_fail

        Args:
            df (pd.DataFrame): The scouting data

        Returns:
            pd.DataFrame: The endgame analysis teams summary
        """
        df["parked"].replace({True: 1, False: 0}, inplace=True)
        df["harmony"].replace({True: 2, False: 0}, inplace=True)
        df["rob_onstage"].replace({1: 3, 2: 3, 3: 3}, inplace=True)
        df["trap_note_pos_amp"].replace({True: 5, False: 0}, inplace=True)
        df["trap_note_pos_source"].replace({True: 5, False: 0}, inplace=True)
        df["trap_note_pos_center"].replace({True: 5, False: 0}, inplace=True)
        df["total_endgame_points"] = (
            df.fillna(0)["parked"]
            + df.fillna(0)["harmony"]
            + df.fillna(0)["rob_onstage"]
            + df.fillna(0)["trap_note_pos_amp"]
            + df.fillna(0)["trap_note_pos_source"]
            + df.fillna(0)["trap_note_pos_center"]
        )

        return self.__get_stats_summary(df, "total_endgame_points")

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
        df["comments"].fillna("", inplace=True)
        group = df.groupby("team_number")
        summary_df = pd.DataFrame(
            [
                group["comments"].aggregate(
                    lambda x: " | ".join(x)
                )  # pylint: disable=W0108
            ]
        ).T.reset_index()
        return summary_df

    def get_picklist_summary(
        self, auto_weight: int, teleop_weight: int, endgame_weight: int
    ) -> pd.DataFrame:
        """Summarize the auto, telop, endgame, and comment data into the final picklist"""
        auto_picklist = pd.DataFrame(
            [
                self.auto_df["team_number"],
                (
                    (
                        self.auto_df[self.metric].rename(f"auto_norm_{self.metric}")
                        - self.auto_df[self.metric].min()
                    )
                    / (
                        self.auto_df[self.metric].max()
                        - self.auto_df[self.metric].min()
                    )
                    * auto_weight
                ),
                self.auto_df["n"],
                self.auto_df["total_passes"],
                self.auto_df["preload%"],
            ]
        ).T

        teleop_picklist = pd.DataFrame(
            [
                self.teleop_df["team_number"],
                (
                    (
                        self.teleop_df[self.metric].rename(f"teleop_norm_{self.metric}")
                        - self.teleop_df[self.metric].min()
                    )
                    / (
                        self.teleop_df[self.metric].max()
                        - self.teleop_df[self.metric].min()
                    )
                    * teleop_weight
                ),
            ]
        ).T

        endgame_picklist = pd.DataFrame(
            [
                self.endgame_df["team_number"],
                (
                    (
                        self.endgame_df[self.metric].rename(
                            f"endgame_norm_{self.metric}"
                        )
                        - self.endgame_df[self.metric].min()
                    )
                    / (
                        self.endgame_df[self.metric].max()
                        - self.endgame_df[self.metric].min()
                    )
                    * endgame_weight
                ),
            ]
        ).T

        comments_picklist = pd.DataFrame(
            [
                self.comments_df["team_number"],
                self.comments_df["comments"],
            ]
        ).T

        picklist_df = pd.merge(auto_picklist, teleop_picklist, on="team_number")
        picklist_df = pd.merge(picklist_df, endgame_picklist, on="team_number")
        picklist_df = pd.merge(picklist_df, comments_picklist, on="team_number")
        picklist_df = picklist_df[
            [
                "team_number",
                f"auto_norm_{self.metric}",
                f"teleop_norm_{self.metric}",
                f"endgame_norm_{self.metric}",
                "n",
                "preload%",
                "total_passes",
                "comments",
            ]
        ]

        picklist_df["team_number"] = picklist_df["team_number"].astype(int)
        picklist_df["n"] = picklist_df["n"].astype(int)

        picklist_score = (
            picklist_df[f"auto_norm_{self.metric}"]
            + picklist_df[f"teleop_norm_{self.metric}"]
            + picklist_df[f"endgame_norm_{self.metric}"]
        )
        picklist_df.insert(1, "picklist_score", picklist_score)
        picklist_df.sort_values("picklist_score", inplace=True, ascending=False)

        return picklist_df

    #     picklist_df.to_csv('./data/picklist_summary.csv', index=False)
    #     scouting_4607.save_to_google_drive(picklist_df, sheet_name)
    #     #print(picklist_df)
