""" The Picklist Analysis Runner
"""

from argparse import ArgumentParser
from os import environ
from dotenv import load_dotenv  # pylint: disable=E0401
import pandas as pd
from .gd import GD
from .tba import TBA
from .sdb import SDB

# from .crescendo_picklist_analysis import CrescendoPicklistAnalysis
from .reefscape_picklist_analysis import ReefscapePicklistAnalysis


if __name__ == "__main__":
    load_dotenv()

    parser = ArgumentParser()
    parser.add_argument("--event_key", required=True, type=str, help="The FIRST FRC event key")
    parser.add_argument(
        "--weights", required=False, type=int, nargs="+", help="auto/teleop/endgame weights, should sum to 100"
    )
    parser.add_argument("--metric", required=False, type=str, help="metric for analysis (mean or median)")
    parser.add_argument("--save", required=False, action="store_true", help="save picklist to Google Drive sheet")
    parser.set_defaults(weights=[40, 20, 20, 20], metric="mean")
    args = parser.parse_args()

    # Get the scouting data for the event
    teams_df = TBA(environ["X-TBA-Auth-Key"]).get_event_team_list(args.event_key)
    sdb_event_df = SDB().get_event_scouting_data(args.event_key)
    scouting_df = pd.merge(teams_df["team_number"], sdb_event_df, on="team_number")

    # Run the analysis
    # picklist_df = CrescendoPicklistAnalysis(scouting_df, args.metric).get_picklist_summary(*args.weights)
    picklist_df = ReefscapePicklistAnalysis(scouting_df, args.metric).get_picklist_summary(*args.weights)

    # Update the Google Drive picklist SS
    if args.save:
        GD(environ["WORKSPACE"]).save_picklist_to_google_drive(picklist_df, args.event_key)
        picklist_df.to_csv("picklist_summary.csv", index=False)

    # # print(CrescendoPicklistAnalysis(scouting_df, args.metric).get_best_passers())
