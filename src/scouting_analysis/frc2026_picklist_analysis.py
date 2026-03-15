"""The 2026 FRC Picklist Analysis Module"""

import pandas as pd
import yaml

# ---------------------------------------------------------------------------
# Point values
# ---------------------------------------------------------------------------
_AUTO_CLIMB_PTS = {"Level1": 15, "Level2": 15, "Level3": 15, "None": 0}
_ENDGAME_CLIMB_PTS = {"Level1": 10, "Level2": 20, "Level3": 30, "None": 0}

# ---------------------------------------------------------------------------
# Weights
# ---------------------------------------------------------------------------
_AUTO_SCOUTING_WEIGHT = 0.0
_AUTO_COPR_WEIGHT = 0.75
_AUTO_EPA_WEIGHT = 0.25
_TELEOP_SCOUTING_WEIGHT = 0.0
_TELEOP_COPR_WEIGHT = 0.75
_TELEOP_EPA_WEIGHT = 0.25
_ENDGAME_TBA_WEIGHT = 0.75
_ENDGAME_EPA_WEIGHT = 0.25


class FRC2026PicklistAnalysis:
    """2026 FRC picklist analysis class.

    Args:
        scouting_df (pd.DataFrame): Scouting database rows for the event.
        metric (str): Summary statistic to rank by (e.g. 'mean', 'median').
        match_breakdowns_df (pd.DataFrame): TBA match breakdown data (may be empty).
        pits_df (pd.DataFrame): Pits database rows for the event.
        coprs_df (pd.DataFrame): TBA COPR data for the event.
        epa_df (pd.DataFrame): Statbotics EPA data for the event.
    """

    def __init__(
        self,
        scouting_df: pd.DataFrame,
        metric: str,
        match_breakdowns_df: pd.DataFrame,
        pits_df: pd.DataFrame,
        coprs_df: pd.DataFrame,
        epa_df: pd.DataFrame = pd.DataFrame(),
    ) -> None:
        self.scouting_df = scouting_df
        self.metric = metric
        self.pits_df = pits_df
        self.coprs_df = coprs_df
        self.epa_df = epa_df

        self.auto_climb_df = (
            self._get_auto_climb_scores(match_breakdowns_df) if not match_breakdowns_df.empty else pd.DataFrame()
        )
        self.endgame_climb_df = (
            self._get_tba_endgame_climb_scores(match_breakdowns_df) if not match_breakdowns_df.empty else pd.DataFrame()
        )
        self.auto_df = self._get_auto_summary()
        self.teleop_df = self._get_teleop_summary()
        self.endgame_df = self._get_tba_endgame_summary()
        self.rank_df = self._get_rank_summary()
        self.breakdown_df = self._get_breakdown_summary()
        self.comments_df = self._get_comments_summary()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def get_picklist_summary(self) -> pd.DataFrame:
        """Merge auto, teleop, endgame, rank, breakdown and comment summaries into a ranked picklist.

        Returns:
            pd.DataFrame: One row per team, sorted descending by total score.
        """
        m = self.metric

        auto_pl = self.auto_df[["team_number", m, "n"]].rename(columns={m: f"auto_{m}"})
        teleop_pl = self.teleop_df[["team_number", m]].rename(columns={m: f"teleop_{m}"})
        endgame_pl = self.endgame_df[["team_number", m]].rename(columns={m: f"endgame_{m}"})
        rank_pl = self.rank_df[["team_number", "drive_rank", "defense_rank"]]
        breakdown_pl = self.breakdown_df[["team_number", "breakdown"]]
        comments_pl = self.comments_df[["team_number", "comments"]]

        df = (
            auto_pl.merge(teleop_pl, on="team_number")
            .merge(endgame_pl, on="team_number", how="left")
            .merge(rank_pl, on="team_number")
            .merge(breakdown_pl, on="team_number")
            .merge(comments_pl, on="team_number")
        )

        score = df[f"auto_{m}"] + df[f"teleop_{m}"] + df[f"endgame_{m}"].fillna(0)

        df.insert(1, "score", score)
        df["team_number"] = df["team_number"].astype(int)
        df["n"] = df["n"].astype(int)
        df.sort_values("score", ascending=False, inplace=True)

        df.rename(
            columns={
                "team_number": "team",
                f"auto_{m}": "auto",
                f"teleop_{m}": "teleop",
                f"endgame_{m}": "endgame",
            },
            inplace=True,
        )

        return df[
            ["team", "score", "auto", "teleop", "endgame", "n", "drive_rank", "defense_rank", "breakdown", "comments"]
        ]

    # ------------------------------------------------------------------ #
    # Private helpers — summaries                                          #
    # ------------------------------------------------------------------ #

    def _get_auto_summary(self) -> pd.DataFrame:
        """Compute per-team autonomous point totals.

        Scoring:
            Weighted blend of scouting (10%), COPR (45%), and Statbotics EPA (45%).
            COPR = Hub Auto Fuel Count + per-robot auto climb score
            EPA = auto_epa from Statbotics

        Returns:
            pd.DataFrame: Stats summary keyed by team_number.
        """
        df = self.scouting_df.copy()
        df["team_number"] = df["team_number"].astype("Int64")

        # Scouting
        df["scouted_auto"] = pd.to_numeric(df["auto_fuel"], errors="coerce").fillna(0)
        scouting_mean = df.groupby("team_number")["scouted_auto"].transform("mean")

        # COPR
        copr_auto = pd.Series(0.0, index=df.index)
        if not self.coprs_df.empty and "Hub Auto Fuel Count" in self.coprs_df.columns:
            coprs = self.coprs_df[["Hub Auto Fuel Count"]].copy()
            coprs["team_number"] = coprs.index.str.replace("frc", "").astype("Int64")
            coprs.rename(columns={"Hub Auto Fuel Count": "copr_auto_fuel"}, inplace=True)
            df = df.merge(coprs[["team_number", "copr_auto_fuel"]], on="team_number", how="left")

            if not self.auto_climb_df.empty:
                df = df.merge(self.auto_climb_df, on="team_number", how="left")
                df["auto_climb_score"] = df["auto_climb_score"].fillna(0)
            else:
                df["auto_climb_score"] = 0.0

            df["total_copr_auto"] = df["copr_auto_fuel"].fillna(0).clip(lower=0) + df["auto_climb_score"]
            copr_auto = df["total_copr_auto"]

        # EPA
        epa_auto = pd.Series(0.0, index=df.index)
        if not self.epa_df.empty and "auto_epa" in self.epa_df.columns:
            epa = self.epa_df[["team_number", "auto_epa"]].copy()
            epa["team_number"] = pd.to_numeric(epa["team_number"], errors="coerce").astype("Int64")
            df = df.merge(epa, on="team_number", how="left")
            epa_auto = df["auto_epa"].fillna(0)

        # Weighted blend
        df["total_auto_points"] = (
            _AUTO_SCOUTING_WEIGHT * scouting_mean + _AUTO_COPR_WEIGHT * copr_auto + _AUTO_EPA_WEIGHT * epa_auto
        )

        # Debug
        print("\n--- Auto Summary Debug ---")
        debug_df = pd.DataFrame(
            {
                "scouting": df.groupby("team_number")["scouted_auto"].mean(),
                "copr": df.groupby("team_number")["total_copr_auto"].first() if "total_copr_auto" in df.columns else 0,
                "epa": df.groupby("team_number")["auto_epa"].first() if "auto_epa" in df.columns else 0,
                "total": df.groupby("team_number")["total_auto_points"].first(),
            }
        ).reset_index()
        sample_teams = [4607] + list(debug_df[debug_df["team_number"] != 4607]["team_number"].sample(9).values)
        print(debug_df[debug_df["team_number"].isin(sample_teams)].set_index("team_number").T.to_string())
        print("--- End Auto Summary Debug ---\n")

        return self._get_stats_summary(df, "total_auto_points")

    def _get_teleop_summary(self) -> pd.DataFrame:
        """Compute per-team teleop point totals.

        Scoring:
            Weighted blend of scouting (10%), COPR (45%), and Statbotics EPA (45%).
            Scouting = cycles * hopper_size
            COPR = Hub Teleop Fuel Count
            EPA = teleop_epa from Statbotics

        Returns:
            pd.DataFrame: Stats summary keyed by team_number.
        """
        df = self.scouting_df.copy()
        df["team_number"] = df["team_number"].astype("Int64")

        # Scouting
        if not self.pits_df.empty and "hopper_size" in self.pits_df.columns:
            hopper = self.pits_df[["team_number", "hopper_size"]].copy()
            hopper["team_number"] = pd.to_numeric(hopper["team_number"], errors="coerce").astype("Int64")
            hopper["hopper_size"] = pd.to_numeric(hopper["hopper_size"], errors="coerce")
            df = df.merge(hopper, on="team_number", how="left")
            df["scouted_teleop"] = pd.to_numeric(df["cycles"], errors="coerce").fillna(0) * df["hopper_size"].fillna(0)
        else:
            df["scouted_teleop"] = 0
        scouting_mean = df.groupby("team_number")["scouted_teleop"].transform("mean")

        # COPR
        copr_teleop = pd.Series(0.0, index=df.index)
        if not self.coprs_df.empty and "Hub Teleop Fuel Count" in self.coprs_df.columns:
            coprs = self.coprs_df[["Hub Teleop Fuel Count"]].copy()
            coprs["team_number"] = coprs.index.str.replace("frc", "").astype("Int64")
            coprs["total_copr_teleop"] = coprs["Hub Teleop Fuel Count"]
            df = df.merge(coprs[["team_number", "total_copr_teleop"]], on="team_number", how="left")
            copr_teleop = df["total_copr_teleop"].fillna(0).clip(lower=0)

        # EPA
        epa_teleop = pd.Series(0.0, index=df.index)
        if not self.epa_df.empty and "teleop_epa" in self.epa_df.columns:
            epa = self.epa_df[["team_number", "teleop_epa"]].copy()
            epa["team_number"] = pd.to_numeric(epa["team_number"], errors="coerce").astype("Int64")
            df = df.merge(epa, on="team_number", how="left")
            epa_teleop = df["teleop_epa"].fillna(0)

        # Weighted blend
        df["total_teleop_points"] = (
            _TELEOP_SCOUTING_WEIGHT * scouting_mean
            + _TELEOP_COPR_WEIGHT * copr_teleop
            + _TELEOP_EPA_WEIGHT * epa_teleop
        )

        # Debug
        print("\n--- Teleop Summary Debug ---")
        debug_df = pd.DataFrame(
            {
                "scouting": df.groupby("team_number")["scouted_teleop"].mean(),
                "copr": df.groupby("team_number")["total_copr_teleop"].first()
                if "total_copr_teleop" in df.columns
                else 0,
                "epa": df.groupby("team_number")["teleop_epa"].first() if "teleop_epa" in df.columns else 0,
                "total": df.groupby("team_number")["total_teleop_points"].first(),
            }
        ).reset_index()
        sample_teams = [4607] + list(debug_df[debug_df["team_number"] != 4607]["team_number"].sample(9).values)
        print(debug_df[debug_df["team_number"].isin(sample_teams)].set_index("team_number").T.to_string())
        print("--- End Teleop Summary Debug ---\n")

        return self._get_stats_summary(df, "total_teleop_points")

    def _get_tba_endgame_summary(self) -> pd.DataFrame:
        """Compute per-team endgame scores blending TBA climb, COPR, and EPA.

        Weights: TBA (climb_score + Hub Endgame Fuel Count) = 50%, EPA endgame = 50%

        Endgame tower: Level1 = 10, Level2 = 20, Level3 = 30, None = 0

        Returns:
            pd.DataFrame: Stats summary keyed by team_number.
        """
        if not self.endgame_climb_df.empty:
            df_merged = self.endgame_climb_df.rename(columns={"endgame_climb_score": "climb_score"}).copy()
        else:
            df_merged = pd.DataFrame(columns=["team_number", "climb_score"])

        # COPR Hub Endgame Fuel Count
        if not self.coprs_df.empty and "Hub Endgame Fuel Count" in self.coprs_df.columns:
            coprs = self.coprs_df[["Hub Endgame Fuel Count"]].copy()
            coprs["team_number"] = coprs.index.str.replace("frc", "").astype("Int64")
            coprs.rename(columns={"Hub Endgame Fuel Count": "copr_endgame_fuel"}, inplace=True)
            df_merged = df_merged.merge(coprs[["team_number", "copr_endgame_fuel"]], on="team_number", how="left")
            df_merged["copr_endgame_fuel"] = df_merged["copr_endgame_fuel"].fillna(0).clip(lower=0)
        else:
            df_merged["copr_endgame_fuel"] = 0.0

        tba_endgame = df_merged["climb_score"] + df_merged["copr_endgame_fuel"]

        # EPA
        epa_endgame = pd.Series(0.0, index=df_merged.index)
        if not self.epa_df.empty and "endgame_epa" in self.epa_df.columns:
            epa = self.epa_df[["team_number", "endgame_epa"]].copy()
            epa["team_number"] = pd.to_numeric(epa["team_number"], errors="coerce").astype("Int64")
            df_merged = df_merged.merge(epa, on="team_number", how="left")
            epa_endgame = df_merged["endgame_epa"].fillna(0).clip(lower=0)

        # Weighted blend
        df_merged["total_endgame_points"] = _ENDGAME_TBA_WEIGHT * tba_endgame + _ENDGAME_EPA_WEIGHT * epa_endgame

        # Debug
        print("\n--- Endgame Summary Debug ---")
        debug_df = pd.DataFrame(
            {
                "climb": df_merged.groupby("team_number")["climb_score"].mean(),
                "copr_fuel": df_merged.groupby("team_number")["copr_endgame_fuel"].first()
                if "copr_endgame_fuel" in df_merged.columns
                else 0,
                "epa": df_merged.groupby("team_number")["endgame_epa"].first()
                if "endgame_epa" in df_merged.columns
                else 0,
                "total": df_merged.groupby("team_number")["total_endgame_points"].first(),
            }
        ).reset_index()
        sample_teams = [4607] + list(debug_df[debug_df["team_number"] != 4607]["team_number"].sample(9).values)
        print(debug_df[debug_df["team_number"].isin(sample_teams)].set_index("team_number").T.to_string())
        print("--- End Endgame Summary Debug ---\n")

        return self._get_stats_summary(df_merged, "total_endgame_points")

    def _get_rank_summary(self) -> pd.DataFrame:
        """Compute mean drive and defense rankings per team.

        Rankings are 1–5 (lower is better).

        Returns:
            pd.DataFrame: Mean drive_rank and defense_rank keyed by team_number.
        """
        df = self.scouting_df.copy()
        df["drive_rank"] = pd.to_numeric(df["drive_rank"], errors="coerce")
        df["defense_rank"] = pd.to_numeric(df["defense_rank"], errors="coerce")
        return df.groupby("team_number")[["drive_rank", "defense_rank"]].mean().reset_index()

    def _get_breakdown_summary(self) -> pd.DataFrame:
        """Count the number of times each team broke down.

        Returns:
            pd.DataFrame: Breakdown count keyed by team_number.
        """
        df = self.scouting_df.copy()
        df["breakdown"] = df["breakdown"].fillna(0).apply(lambda x: 1 if x else 0)
        return df.groupby("team_number")["breakdown"].sum().reset_index()

    def _get_comments_summary(self) -> pd.DataFrame:
        """Concatenate all scouter comments per team.

        Returns:
            pd.DataFrame: Joined comments keyed by team_number.
        """
        df = self.scouting_df.copy()
        df["comments"] = df["comments"].fillna("")
        return df.groupby("team_number")["comments"].apply(" | ".join).reset_index()

    def _get_auto_climb_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract per-team auto tower climb scores from TBA match breakdowns.

        Auto tower: any level = 15 pts

        Args:
            df (pd.DataFrame): TBA match breakdowns DataFrame.

        Returns:
            pd.DataFrame: Mean auto climb score keyed by team_number.
        """
        records = []
        for _, row in df.iterrows():
            if pd.isna(row["score_breakdown"]) or pd.isna(row["alliances"]):
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
                    auto_pts = _AUTO_CLIMB_PTS.get(auto_climb, 0)
                    records.append(
                        {
                            "team_number": team,
                            "auto_climb_score": auto_pts,
                        }
                    )

        climb_df = pd.DataFrame(records)
        climb_df["team_number"] = climb_df["team_number"].astype("Int64")
        return climb_df.groupby("team_number")["auto_climb_score"].mean().reset_index()

    def _get_tba_endgame_climb_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract per-team endgame tower climb scores from TBA match breakdowns.

        Endgame tower: Level1 = 10, Level2 = 20, Level3 = 30, None = 0

        Args:
            df (pd.DataFrame): TBA match breakdowns DataFrame.

        Returns:
            pd.DataFrame: Mean endgame climb score keyed by team_number.
        """
        records = []
        for _, row in df.iterrows():
            if pd.isna(row["score_breakdown"]) or pd.isna(row["alliances"]):
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
                    endgame_climb = scores.get(f"endGameTowerRobot{idx + 1}", "None")
                    endgame_pts = _ENDGAME_CLIMB_PTS.get(endgame_climb, 0)
                    records.append(
                        {
                            "team_number": team,
                            "endgame_climb_score": endgame_pts,
                        }
                    )

        climb_df = pd.DataFrame(records)
        climb_df["team_number"] = climb_df["team_number"].astype("Int64")
        return climb_df.groupby("team_number")["endgame_climb_score"].mean().reset_index()

    # ------------------------------------------------------------------ #
    # Private helpers — stats                                              #
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
