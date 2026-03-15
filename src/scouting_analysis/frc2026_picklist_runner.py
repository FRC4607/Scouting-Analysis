"""The 2026 FRC Picklist Analysis Runner"""

from argparse import ArgumentParser
from os import environ

import pandas as pd
import yaml
from dotenv import load_dotenv  # type: ignore

from .frc2026_picklist_analysis import FRC2026PicklistAnalysis
from .gd import GD
from .sdb import SDB
from .tba import TBA


def main():
    load_dotenv()

    parser = ArgumentParser(description="Run the 2026 FRC picklist analysis.")
    parser.add_argument("--event_key", required=True, type=str, help="The FIRST FRC event key")
    parser.add_argument("--metric", required=False, type=str, default="mean", help="Ranking metric: 'mean' or 'median'")
    parser.add_argument("--save", required=False, action="store_true", help="Save picklist to Google Drive")
    parser.add_argument("--teams", required=False, type=int, nargs="+", help="List of specific teams to analyze")
    args = parser.parse_args()

    tba = TBA(environ["X-TBA-Auth-Key"])
    sdb = SDB()

    # ------------------------------------------------------------------ #
    # Scouting data                                                      #
    # ------------------------------------------------------------------ #
    if args.teams:
        scouting_df = sdb.get_teams_scouting_data(args.teams, force=True)
        pits_df = sdb.get_teams_pits_data(args.teams, force=True)
    else:
        sdb_event_df = sdb.get_event_scouting_data(args.event_key, force=True)
        pits_df = sdb.get_event_pits_data(args.event_key, force=False)
        teams_df = tba.get_event_team_list(args.event_key, force=True)
        scouting_df = pd.merge(teams_df["team_number"], sdb_event_df, on="team_number")

    # ------------------------------------------------------------------ #
    # TBA match breakdowns and insights                                  #
    # ------------------------------------------------------------------ #
    match_breakdowns_df = tba.get_event_match_breakdowns(args.event_key, force=True)
    coprs_df = tba.get_event_coprs(args.event_key, force=True)

    # ------------------------------------------------------------------ #
    # Picklist analysis                                                  #
    # ------------------------------------------------------------------ #
    rpa = FRC2026PicklistAnalysis(scouting_df, args.metric, match_breakdowns_df, pits_df, coprs_df)
    picklist_df = rpa.get_picklist_summary()

    # ------------------------------------------------------------------ #
    # Match planner                                                      #
    # ------------------------------------------------------------------ #
    matches_df = tba.get_event_matches(args.event_key, force=True)

    matches = {}
    for _, row in matches_df.iterrows():
        if row["comp_level"] != "qm":
            continue
        alliances = row["alliances"] if isinstance(row["alliances"], dict) else yaml.safe_load(row["alliances"])
        matches[int(row["match_number"])] = [
            alliances["blue"]["team_keys"],
            alliances["red"]["team_keys"],
        ]

    stages = ["auto", "teleop"]
    stage_dfs = [rpa.auto_df, rpa.teleop_df]
    if rpa.climb_df is not None:
        stages.append("climb")
        stage_dfs.append(rpa.climb_df)

    planner_df = pd.DataFrame()
    for match, (blue_teams, red_teams) in sorted(matches.items()):
        alliance_dfs = []
        for alliance_teams in (blue_teams, red_teams):
            alliance_df = pd.DataFrame()
            for team_key in alliance_teams:
                team = int(team_key[3:])
                team_rows = []
                for stage, df in zip(stages, stage_dfs):
                    row = df.loc[df["team_number"] == team]
                    if row.empty:
                        row = pd.DataFrame([{"team_number": team}])
                    row = row.copy()
                    row["stage"] = stage
                    team_rows.append(row)
                team_df = pd.concat(team_rows)
                team_df.insert(0, "match#", match)
                alliance_df = pd.concat([alliance_df, team_df])
            alliance_dfs.append(alliance_df)

        right = alliance_dfs[1].reset_index(drop=True).drop(columns=["match#"])
        match_df = pd.concat([alliance_dfs[0].reset_index(drop=True), right], axis=1)
        match_df = pd.concat(
            [match_df, pd.DataFrame([""] * len(match_df.columns), index=match_df.columns).T],
            ignore_index=True,
        )
        planner_df = pd.concat([planner_df, match_df])

    # ------------------------------------------------------------------ #
    # Save outputs                                                       #
    # ------------------------------------------------------------------ #
    if args.save:
        gd = GD(environ["WORKSPACE"])
        gd.save_match_planning_to_google_drive(planner_df, args.event_key)
        gd.save_picklist_to_google_drive(picklist_df, args.event_key)
        picklist_df.to_csv("picklist_summary.csv", index=False)


if __name__ == "__main__":
    main()
