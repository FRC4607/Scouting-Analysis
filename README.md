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
    - python -m scouting_analysis.picklist_runner --event_key 2025mndu --save
