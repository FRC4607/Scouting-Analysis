"""The Picklist Analysis Runner"""

from argparse import ArgumentParser
from os import environ
from dotenv import load_dotenv  # pylint: disable=E0401
import pandas as pd
import yaml  # pylint: disable=E0401
from .gd import GD
from .tba import TBA
from .sdb import SDB
from .reefscape_picklist_analysis import ReefscapePicklistAnalysis


if __name__ == "__main__":
    load_dotenv()

    parser = ArgumentParser()
    parser.add_argument("--event_key", required=True, type=str, help="The FIRST FRC event key used to get teams list")
    parser.add_argument("--metric", required=False, type=str, help="metric for analysis (mean or median)")
    parser.add_argument("--use_tba", required=False, action="store_true", help="use TBA data for endgame")
    parser.add_argument("--save", required=False, action="store_true", help="save picklist to Google Drive sheet")
    parser.add_argument("--teams", required=False, type=int, nargs="+", help="list of teams to analyze")
    parser.set_defaults(metric="mean")
    args = parser.parse_args()

    # Get the scouting data for the event or given list of teams
    if args.teams:
        sdb_event_df = SDB().get_teams_scouting_data(args.teams, force=True)
        sdb_event_df["ScoutedTime"] = pd.to_datetime(sdb_event_df["ScoutedTime"])
        # scouting_df = sdb_event_df[sdb_event_df["ScoutedTime"] > pd.to_datetime("2025-04-15")]
        scouting_df = sdb_event_df[sdb_event_df["ScoutedTime"] > pd.to_datetime("2025-05-09")]

    else:
        sdb_event_df = SDB().get_event_scouting_data(args.event_key, force=True)
        teams_df = TBA(environ["X-TBA-Auth-Key"]).get_event_team_list(args.event_key, force=True)
        scouting_df = pd.merge(teams_df["team_number"], sdb_event_df, on="team_number")

    # Run the picklist analysis
    match_breakdowns_df = pd.DataFrame()
    if args.use_tba:
        match_breakdowns_df = TBA(environ["X-TBA-Auth-Key"]).get_event_match_breakdowns(args.event_key, force=True)
    RPA = ReefscapePicklistAnalysis(scouting_df, args.metric, match_breakdowns_df)
    picklist_df = RPA.get_picklist_summary()

    # Get the matches for the event
    matches_df = TBA(environ["X-TBA-Auth-Key"]).get_event_matches(args.event_key, force=True)

    # Get the scouting data for the matches
    matches = {}
    for _, row in matches_df.iterrows():
        if row["comp_level"] == "sf":  # qm or sf
            continue
        matches[int(row["match_number"])] = [
            yaml.load(row["alliances"], Loader=yaml.Loader)["blue"]["team_keys"],
            yaml.load(row["alliances"], Loader=yaml.Loader)["red"]["team_keys"],
        ]

    planner_df = pd.DataFrame()
    for match, teams in sorted(matches.items()):
        blue_teams = teams[1]
        red_teams = teams[0]

        blue_df = pd.DataFrame()
        for team in blue_teams:
            team_df = pd.concat(
                [
                    RPA.auto_df.loc[RPA.auto_df["team_number"] == int(team[3:])],
                    RPA.teleop_coral_df.loc[RPA.teleop_coral_df["team_number"] == int(team[3:])],
                    RPA.teleop_algae_df.loc[RPA.teleop_algae_df["team_number"] == int(team[3:])],
                    RPA.endgame_df.loc[RPA.endgame_df["team_number"] == int(team[3:])],
                ]
            )
            team_df["stage"] = ["auto", "coral", "algae", "endgame"]
            team_df["match#"] = [match, match, match, match]
            blue_df = pd.concat([blue_df, team_df])

        red_df = pd.DataFrame()
        for team in red_teams:
            team_df = pd.concat(
                [
                    RPA.auto_df.loc[RPA.auto_df["team_number"] == int(team[3:])],
                    RPA.teleop_coral_df.loc[RPA.teleop_coral_df["team_number"] == int(team[3:])],
                    RPA.teleop_algae_df.loc[RPA.teleop_algae_df["team_number"] == int(team[3:])],
                    RPA.endgame_df.loc[RPA.endgame_df["team_number"] == int(team[3:])],
                ]
            )
            team_df["stage"] = ["auto", "coral", "algae", "endgame"]
            red_df = pd.concat([red_df, team_df])

        match_df = pd.concat([blue_df.reset_index(drop=True), red_df.reset_index(drop=True)], axis=1)
        match_df = pd.concat(
            [match_df, pd.DataFrame([""] * len(match_df.columns), index=match_df.columns).T], ignore_index=True
        )
        planner_df = pd.concat([planner_df, match_df])

    # Update the Google Drive picklist SS
    if args.save:
        GD(environ["WORKSPACE"]).save_match_planning_to_google_drive(planner_df, args.event_key)
        GD(environ["WORKSPACE"]).save_picklist_to_google_drive(picklist_df, args.event_key)
        picklist_df.to_csv("picklist_summary.csv", index=False)
