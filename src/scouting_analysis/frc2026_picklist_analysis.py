"""The 2026 FRC Picklist Analysis Module"""

import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# Point values
# ---------------------------------------------------------------------------
_AUTO_CLIMB_PTS = {"Level1": 15, "Level2": 15, "Level3": 15, "None": 0}
_ENDGAME_CLIMB_PTS = {"Level1": 10, "Level2": 20, "Level3": 30, "None": 0}


class FRC2026PicklistAnalysis:
    """2026 FRC picklist analysis class.

    Args:
        scouting_df (pd.DataFrame): Scouting database rows for the event.
        metric (str): Summary statistic to rank by (e.g. 'mean', 'median').
        match_breakdowns_df (pd.DataFrame): TBA match breakdown data (may be empty).
    """

    def __init__(
        self,
        scouting_df: pd.DataFrame,
        metric: str,
        match_breakdowns_df: pd.DataFrame,
        pits_df: pd.DataFrame,
        coprs_df: pd.DataFrame,
    ) -> None:
        self.scouting_df = scouting_df
        self.metric = metric
        self.pits_df = pits_df
        self.coprs_df = coprs_df

        self.auto_df = self._get_auto_summary(self.scouting_df)
        self.teleop_df = self._get_teleop_summary(self.scouting_df)
        self.climb_df = self._get_tba_endgame_summary(match_breakdowns_df) if not match_breakdowns_df.empty else None
        self.rank_df = self._get_rank_summary(self.scouting_df)
        self.breakdown_df = self._get_breakdown_summary(self.scouting_df)
        self.comments_df = self._get_comments_summary(self.scouting_df)

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def get_picklist_summary(self) -> pd.DataFrame:
        """Merge auto, teleop, climb, rank, breakdown and comment summaries into a ranked picklist.

        Returns:
            pd.DataFrame: One row per team, sorted descending by total score.
        """
        m = self.metric

        auto_pl = self.auto_df[["team_number", m, "n"]].rename(columns={m: f"auto_{m}"})
        teleop_pl = self.teleop_df[["team_number", m]].rename(columns={m: f"teleop_{m}"})
        rank_pl = self.rank_df[["team_number", "drive_rank", "defense_rank"]]
        breakdown_pl = self.breakdown_df[["team_number", "breakdown"]]
        comments_pl = self.comments_df[["team_number", "comments"]]

        df = (
            auto_pl.merge(teleop_pl, on="team_number")
            .merge(rank_pl, on="team_number")
            .merge(breakdown_pl, on="team_number")
            .merge(comments_pl, on="team_number")
        )

        score = df[f"auto_{m}"] + df[f"teleop_{m}"]

        if self.climb_df is not None:
            climb_pl = self.climb_df[["team_number", m]].rename(columns={m: f"climb_{m}"})
            df = df.merge(climb_pl, on="team_number", how="left")
            score = score + df[f"climb_{m}"].fillna(0)

        df.insert(1, "score", score)
        df["team_number"] = df["team_number"].astype(int)
        df["n"] = df["n"].astype(int)
        df.sort_values("score", ascending=False, inplace=True)

        rename = {
            "team_number": "team",
            f"auto_{m}": "auto",
            f"teleop_{m}": "teleop",
        }
        if self.climb_df is not None:
            rename[f"climb_{m}"] = "climb"

        df.rename(columns=rename, inplace=True)

        cols = ["team", "score", "auto", "teleop"]
        if self.climb_df is not None:
            cols.append("climb")
        cols += ["n", "drive_rank", "defense_rank", "breakdown", "comments"]

        return df[cols]

    # ------------------------------------------------------------------ #
    # Private helpers — summaries                                        #
    # ------------------------------------------------------------------ #

    def _get_auto_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute per-team autonomous point totals.

        Scoring:
            auto_fuel = 1 pt each, anchored to COPR Hub Auto Fuel Count
            adjusted by 25% of the delta between COPR and scouted mean.

        Args:
            df (pd.DataFrame): Raw scouting data.

        Returns:
            pd.DataFrame: Stats summary keyed by team_number.
        """
        df = df.copy()
        df["scouted_auto_fuel"] = pd.to_numeric(df["auto_fuel"], errors="coerce").fillna(0)

        if not self.coprs_df.empty and "Hub Auto Fuel Count" in self.coprs_df.columns:
            coprs = self.coprs_df[["Hub Auto Fuel Count"]].copy()
            coprs["team_number"] = coprs.index.str.replace("frc", "").astype("Int64")
            coprs.rename(columns={"Hub Auto Fuel Count": "total_copr_auto_fuel"}, inplace=True)
            df["team_number"] = df["team_number"].astype("Int64")
            df = df.merge(coprs[["team_number", "total_copr_auto_fuel"]], on="team_number", how="left")

            scouted_mean = df.groupby("team_number")["scouted_auto_fuel"].transform("mean")
            delta = df["total_copr_auto_fuel"].fillna(0) - scouted_mean
            df["total_auto_points"] = df["total_copr_auto_fuel"].fillna(0) - delta * 0.1
        else:
            df["total_auto_points"] = df["scouted_auto_fuel"]

        return self._get_stats_summary(df, "total_auto_points")

    def _get_teleop_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute per-team teleop point totals.

        Scoring:
            Uses COPR Hub Teleop + Endgame Fuel Count as the base estimate,
            adjusted by 25% of the delta between COPR and scouted mean.

        Args:
            df (pd.DataFrame): Raw scouting data.

        Returns:
            pd.DataFrame: Stats summary keyed by team_number.
        """
        df = df.copy()

        # Compute scouted fuel estimate per match
        if not self.pits_df.empty and "hopper_size" in self.pits_df.columns:
            hopper = self.pits_df[["team_number", "hopper_size"]].copy()
            hopper["team_number"] = pd.to_numeric(hopper["team_number"], errors="coerce").astype("Int64")
            hopper["hopper_size"] = pd.to_numeric(hopper["hopper_size"], errors="coerce")
            df["team_number"] = df["team_number"].astype("Int64")
            df = df.merge(hopper, on="team_number", how="left")
            df["scouted_fuel"] = pd.to_numeric(df["cycles"], errors="coerce").fillna(0) * df["hopper_size"].fillna(0)
        else:
            df["scouted_fuel"] = 0

        if not self.coprs_df.empty and "Hub Teleop Fuel Count" in self.coprs_df.columns:
            coprs = self.coprs_df[["Hub Teleop Fuel Count", "Hub Endgame Fuel Count"]].copy()
            coprs.index = coprs.index.str.replace("frc", "").astype("Int64")
            coprs.index.name = "team_number"
            coprs = coprs.reset_index()
            coprs["total_copr_fuel"] = coprs["Hub Teleop Fuel Count"] + coprs["Hub Endgame Fuel Count"]
            df = df.merge(coprs[["team_number", "total_copr_fuel"]], on="team_number", how="left")

            scouted_mean = df.groupby("team_number")["scouted_fuel"].transform("mean")
            delta = df["total_copr_fuel"].fillna(0) - scouted_mean
            df["total_teleop_points"] = df["total_copr_fuel"].fillna(0) - delta * 0.1
        else:
            df["total_teleop_points"] = df["scouted_fuel"]

        return self._get_stats_summary(df, "total_teleop_points")

    def _get_tba_endgame_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute per-team climb scores from TBA match breakdown data.

        Auto tower:    any level = 15 pts
        Endgame tower: Level1 = 10, Level2 = 20, Level3 = 30, None = 0

        Args:
            df (pd.DataFrame): TBA match breakdowns DataFrame.

        Returns:
            pd.DataFrame: Stats summary keyed by team_number.
        """
        records = []

        for _, row in df.iterrows():
            if pd.isna(row["score_breakdown"]) or pd.isna(row["alliances"]):
                continue
            if row["score_breakdown"] is None or row["alliances"] is None:
                continue
            score_breakdown = (
                row["score_breakdown"]
                if isinstance(row["score_breakdown"], dict)
                else yaml.safe_load(row["score_breakdown"])
            )
            alliances = row["alliances"] if isinstance(row["alliances"], dict) else yaml.safe_load(row["alliances"])

            for alliance in ("blue", "red"):
                scores = score_breakdown[alliance]
                teams = alliances[alliance]["team_keys"]

                for idx, team_key in enumerate(teams):
                    team = int(team_key[3:])

                    auto_climb = scores.get(f"autoTowerRobot{idx + 1}", "None")
                    endgame_climb = scores.get(f"endGameTowerRobot{idx + 1}", "None")

                    auto_pts = _AUTO_CLIMB_PTS.get(auto_climb, 0)
                    endgame_pts = _ENDGAME_CLIMB_PTS.get(endgame_climb, 0)

                    records.append(
                        {
                            "team_number": team,
                            "auto_climb": auto_climb,
                            "auto_climb_score": auto_pts,
                            "endgame_climb": endgame_climb,
                            "endgame_climb_score": endgame_pts,
                            "total_climb_score": auto_pts + endgame_pts,
                        }
                    )

        climb_df = pd.DataFrame(records)
        return self._get_stats_summary(climb_df, "total_climb_score")

    def _get_rank_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute mean drive and defense rankings per team.

        Rankings are 1–5 (lower is better).

        Args:
            df (pd.DataFrame): Raw scouting data.

        Returns:
            pd.DataFrame: Mean drive_rank and defense_rank keyed by team_number.
        """
        df = df.copy()
        df["drive_rank"] = pd.to_numeric(df["drive_rank"], errors="coerce")
        df["defense_rank"] = pd.to_numeric(df["defense_rank"], errors="coerce")
        return df.groupby("team_number")[["drive_rank", "defense_rank"]].mean().reset_index()

    def _get_breakdown_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Count the number of times each team broke down.

        Args:
            df (pd.DataFrame): Raw scouting data.

        Returns:
            pd.DataFrame: Breakdown count keyed by team_number.
        """
        df = df.copy()
        df["breakdown"] = df["breakdown"].fillna(0).apply(lambda x: 1 if x else 0)
        return df.groupby("team_number")["breakdown"].sum().reset_index()

    def _get_comments_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Concatenate all scouter comments per team.

        Args:
            df (pd.DataFrame): Raw scouting data.

        Returns:
            pd.DataFrame: Joined comments keyed by team_number.
        """
        df = df.copy()
        df["comments"] = df["comments"].fillna("")
        return df.groupby("team_number")["comments"].apply(" | ".join).reset_index()

    # ------------------------------------------------------------------ #
    # Private helpers — stats                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _get_stats_summary(df: pd.DataFrame, col: str) -> pd.DataFrame:
        """Compute descriptive statistics for a column, grouped by team.

        Args:
            df (pd.DataFrame): Input data containing 'team_number' and col.
            col (str): Column to compute statistics on.

        Returns:
            pd.DataFrame: One row per team with columns: n, mean, median, std, min, max.
        """
        group = df.groupby("team_number")[col]
        return (
            pd.concat(
                [
                    group.count().rename("n"),
                    group.mean().rename("mean"),
                    group.median().rename("median"),
                    group.std().rename("std"),
                    group.min().rename("min"),
                    group.max().rename("max"),
                ],
                axis=1,
            )
            .reset_index()
            .sort_values("mean", ascending=False)
        )
