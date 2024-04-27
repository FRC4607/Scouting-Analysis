""" The Picklist Analysis Runner
"""

from os import environ
from dotenv import load_dotenv  # pylint: disable=E0401
import pandas as pd
from .tba import TBA
from .sdb import SDB
from .crescendo_picklist_analysis import CrescendoPicklistAnalysis

load_dotenv()


# Add CLI inputs --event, --force
EVENT_KEY = "2024new"

# Get the scouting data for the event
teams_df = TBA(environ["X-TBA-Auth-Key"]).get_event_team_list(EVENT_KEY)
sdb_df = SDB().get_scouting_data()
sdb_event_df = (
    sdb_df[sdb_df["event_key"] == EVENT_KEY].drop("id", axis=1).drop_duplicates()
)
scouting_df = pd.merge(teams_df["team_number"], sdb_event_df, on="team_number")

# Run the analysis
print(CrescendoPicklistAnalysis(scouting_df, "mean").get_picklist_summary(45, 45, 10))

# if __name__ == "__main__":

#     #-------------------------------------------------------------
#     # TUNABLE PARAMETERS
#     #-------------------------------------------------------------
#     AUTO_WEIGHT = 45
#     TELEOP_WEIGHT = 45
#     END_WEIGHT = 10
#     EVENT_KEY = '2024new'  #'2024mnmi2' #'2024iacf' #'2024ndgf' #'2024mndu' #'2024mndu2'
#     METRIC = 'mean'

#     auto_picklist = get_autonomous_picklist(scouting_df)
#     teleop_picklist = get_teleop_picklist(scouting_df)
#     endgame_picklist = get_endgame_picklist(scouting_df)
#     comments_picklist = get_comments_picklist(scouting_df)

#     picklist_summary(EVENT_KEY, auto_picklist, teleop_picklist, endgame_picklist, comments_picklist)
#     scouting_df.to_csv('./data/scouting_summary.csv', index=False)
