"""The Statbotics API Module
TODO: This module isn't complete. Just got something going for state 2024.
"""

import statbotics


AUTO = "auto_epa_end"
TELEOP = "teleop_epa_end"
END = "endgame_epa_end"


sb = statbotics.Statbotics()
team_epa = {}
match_schedule = [
    ([2129, 3630, 4607], [3102, 5232, 4728]),
    ([4728, 2977, 4607], [7257, 3018, 5348]),
    ([5348, 6045, 4607], [5172, 2531, 2491]),
    ([2530, 4230, 4607], [2470, 9576, 6147]),
    ([2531, 1816, 4607], [3630, 9576, 2530]),
    ([7257, 3102, 4607], [2823, 9745, 2530]),
    ([4239, 3277, 4607], [2129, 9745, 4539]),
    ([4539, 3184, 4607], [6045, 5434, 2531]),
]


def update_team_epa(teams: list):
    """_summary_

    Args:
        teams (list): _description_
    """
    for team in teams:
        if team not in team_epa:
            team_epa[team] = sb.get_team_year(team, 2024, [AUTO, TELEOP, END])


def get_alliance_epa(teams: list) -> float:
    """_summary_

    Args:
        teams (list): _description_

    Returns:
        float: _description_
    """
    total = 0.0
    for team in teams:
        total += team_epa[team][AUTO] + team_epa[team][TELEOP] + team_epa[team][END]
    return total


print("Our Alliance Total  Opposing Allinace Total  Win/Lose")
for partners, enemies in match_schedule:
    update_team_epa(partners + enemies)
    us = get_alliance_epa(partners)
    them = get_alliance_epa(enemies)
    if us > them:
        WINLOSE = "Win"
    elif us < them:
        WINLOSE = "Lose"
    else:
        WINLOSE = "Tie"

    print(f"{us:18.1f}{them:25.1f}{WINLOSE:>10}")
