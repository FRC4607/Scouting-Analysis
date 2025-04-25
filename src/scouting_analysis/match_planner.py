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
    parser.add_argument("--event_key", required=True, type=str, help="The FIRST FRC event key")
    args = parser.parse_args()

    # Get the scouting data for the event
    teams_df = TBA(environ["X-TBA-Auth-Key"]).get_event_team_list(args.event_key, force=True)
    # match_breakdowns_df = TBA(environ["X-TBA-Auth-Key"]).get_event_match_breakdowns(args.event_key, force=False)
    matches_df = TBA(environ["X-TBA-Auth-Key"]).get_event_matches(args.event_key, force=True)
    sdb_event_df = SDB().get_event_scouting_data(args.event_key, force=True)
    scouting_df = pd.merge(teams_df["team_number"], sdb_event_df, on="team_number")

    # Compile the data
    match_breakdowns_df = pd.DataFrame()
    RPA = ReefscapePicklistAnalysis(scouting_df, "mean", match_breakdowns_df)
    # RPA = ReefscapePicklistAnalysis(scouting_df, "mean")

    # Get the scouting data for the matches
    matches = {}
    for _, row in matches_df.iterrows():
        if row["comp_level"] == "sf":  # qm or sf
            continue
        matches[int(row["match_number"])] = [
            yaml.load(row["alliances"], Loader=yaml.Loader)["blue"]["team_keys"],
            yaml.load(row["alliances"], Loader=yaml.Loader)["red"]["team_keys"],
        ]

    df = pd.DataFrame()
    for match, teams in sorted(matches.items()):
        blue_teams = teams[0]
        red_teams = teams[1]

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
        df = pd.concat([df, match_df])

    GD(environ["WORKSPACE"]).save_match_planning_to_google_drive(df, args.event_key)
