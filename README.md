# Scouting-Analysis

This python project provides the tools necessary to analyze 4607's scouting data.

## Installation Instructions

1. Start VS Code
2. Clone this repository to your local workspace
3. Create a new file in the root and name it ".env"
4. Add the following environment variable to the ".env" file: PYTHONPYCACHEPREFIX="C:\Windows\Temp\"
5. Add the following environment variable to the ".env" file: X-TBA-Auth-Key="use your personal TBA API key"
6. Add the following environment variable to the ".env" file: WORKSPACE="path to this cloned repo"
7. Open a CMD shell in VS Code and run the following:
    - setup
    - cd "to your working directory"
    python -m scouting_analysis.picklist_runner --event_key 2025dal --save --use_tba
    python -m scouting_analysis.match_planner --event_key 2025dal
    python -m scouting_analysis.picklist_runner --event_key 2025mnst --save --use_tba
    python -m scouting_analysis.picklist_runner --event_key 2025mndu --save --use_tba
    python -m scouting_analysis.picklist_runner --event_key 2025state --save --teams 3276 4607 2530 6147 5913 2847 4728 2129 2052 7257 2491 7028 3297 3313 6045 3130 9576 3100 5653 4009 5348 2883 2987 3082 6146 3883 7541 2472 2470 3102 3058 2480 6749 6132 2225 7530
