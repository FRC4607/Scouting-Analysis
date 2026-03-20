"""The 2026 FRC Picklist Analysis Runner"""

import base64
import json
from argparse import ArgumentParser
from os import environ

import pandas as pd
import requests
import yaml
from dotenv import load_dotenv  # type: ignore

from .frc2026_picklist_analysis import FRC2026PicklistAnalysis
from .sb import SB
from .sdb import SDB
from .tba import TBA


def push_to_github(data: dict, event_key: str) -> None:
    """Push match planner JSON to GitHub repo.

    Args:
        data (dict): Match planner data to push.
        event_key (str): Event key used as filename.
    """
    token = environ["GITHUB_TOKEN"]
    repo = "FRC4607/Scouting-Analysis"
    filename = f"webapp/{event_key}.json"
    api_url = f"https://api.github.com/repos/{repo}/contents/{filename}"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Check if file already exists to get its SHA (required for updates)
    resp = requests.get(api_url, headers=headers)
    sha = resp.json().get("sha") if resp.status_code == 200 else None

    content = base64.b64encode(json.dumps(data, indent=2).encode()).decode()

    payload = {
        "message": f"Update match planner data for {event_key}",
        "content": content,
    }
    if sha:
        payload["sha"] = sha

    resp = requests.put(api_url, headers=headers, json=payload)
    if resp.status_code in (200, 201):
        print(f"Pushed {filename} to GitHub.")
    else:
        print(f"Failed to push to GitHub: {resp.text}")


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
    sb = SB()

    # ------------------------------------------------------------------ #
    # Scouting data                                                        #
    # ------------------------------------------------------------------ #
    if args.teams:
        scouting_df = sdb.get_teams_scouting_data(args.teams, force=True)
        pits_df = sdb.get_teams_pits_data(args.teams, force=True)
    else:
        sdb_event_df = sdb.get_event_scouting_data(args.event_key, force=True)
        pits_df = sdb.get_event_pits_data(args.event_key, force=True)
        teams_df = tba.get_event_team_list(args.event_key, force=True)
        scouting_df = pd.merge(teams_df["team_number"], sdb_event_df, on="team_number")

    # ------------------------------------------------------------------ #
    # TBA match breakdowns, COPRs, and OPRs                              #
    # ------------------------------------------------------------------ #
    match_breakdowns_df = tba.get_event_match_breakdowns(args.event_key, force=True)
    coprs_df = tba.get_event_coprs(args.event_key, force=True)
    oprs_df = tba.get_event_oprs(args.event_key, force=True)

    # ------------------------------------------------------------------ #
    # Statbotics EPA data                                                  #
    # ------------------------------------------------------------------ #
    epa_df = sb.get_event_team_stats(args.event_key, force=True)

    # ------------------------------------------------------------------ #
    # Picklist analysis                                                    #
    # ------------------------------------------------------------------ #
    rpa = FRC2026PicklistAnalysis(scouting_df, args.metric, match_breakdowns_df, pits_df, coprs_df, epa_df)
    picklist_df = rpa.get_picklist_summary()

    # ------------------------------------------------------------------ #
    # Match planner                                                        #
    # ------------------------------------------------------------------ #
    matches_df = tba.get_event_matches(args.event_key, force=True)

    matches = {}
    for _, row in matches_df.iterrows():
        if row["comp_level"] != "qm":
            continue
        alliances = row["alliances"] if isinstance(row["alliances"], dict) else yaml.safe_load(row["alliances"])
        matches[int(row["match_number"])] = {
            "blue": [int(t[3:]) for t in alliances["blue"]["team_keys"]],
            "red": [int(t[3:]) for t in alliances["red"]["team_keys"]],
        }

    # Build a lookup from picklist
    picklist_lookup = picklist_df.set_index("team")

    def get_stat(team, col):
        try:
            val = picklist_lookup.loc[team, col]
            return round(float(val), 1) if pd.notna(val) else ""
        except (KeyError, TypeError):
            try:
                team_key = f"frc{team}"
                val = coprs_df.loc[team_key, col]
                return round(float(val), 1) if pd.notna(val) else ""
            except (KeyError, TypeError):
                try:
                    team_key = f"frc{team}"
                    val = oprs_df.loc[team_key, col]
                    return round(float(val), 1) if pd.notna(val) else ""
                except (KeyError, TypeError):
                    return ""

    rows = []
    for match_num, alliances in sorted(matches.items()):
        blue = alliances["blue"]
        red = alliances["red"]
        teams = blue + red

        blue_total = sum(get_stat(t, "score") or 0 for t in blue)
        red_total = sum(get_stat(t, "score") or 0 for t in red)

        # Match header row
        alliance_4607 = "BLUE" if 4607 in blue else "RED"
        rows.append(
            [f"Match {match_num} — {alliance_4607}", "", "", round(blue_total, 1), "", "", "", round(red_total, 1), ""]
        )

        # Column header row
        rows.append(["", "blue1", "blue2", "blue3", "", "red1", "red2", "red3", ""])

        # Data rows
        for metric, col in [
            ("team", None),
            ("auto", "auto"),
            ("teleop", "teleop"),
            ("endgame", "endgame"),
            ("total", "score"),
            ("fouls", "foulPoints"),
            ("dpr", "dprs"),
            ("drive", "drive_rank"),
            ("defense", "defense_rank"),
        ]:
            values = [int(t) for t in teams] if col is None else [get_stat(t, col) for t in teams]
            rows.append([metric] + list(values[:3]) + [""] + list(values[3:]) + [""])

        if match_num != sorted(matches.keys())[-1]:
            rows.append([""] * 9)

        # Blank separator row
        rows.append([""] * 9)

    planner_df = pd.DataFrame(rows, columns=["metric", "blue1", "blue2", "blue3", "sep", "red1", "red2", "red3", "end"])

    # ------------------------------------------------------------------ #
    # Save outputs                                                       #
    # ------------------------------------------------------------------ #
    if args.save:
        picklist_df.to_csv("picklist_summary.csv", index=False)

        # Build and push match planner JSON
        match_data = {}
        current_match = None
        for _, row in planner_df.iterrows():
            first = str(row.iloc[0]).strip()
            if first.startswith("Match "):
                parts = first.split(" — ")
                num = int(parts[0].replace("Match ", ""))
                alliance = parts[1].strip() if len(parts) > 1 else ""
                current_match = str(num)
                match_data[current_match] = {
                    "num": num,
                    "alliance": alliance,
                    "blueTotal": float(row.iloc[3]) if row.iloc[3] != "" else 0,
                    "redTotal": float(row.iloc[7]) if row.iloc[7] != "" else 0,
                    "rows": [],
                }
            elif current_match and first not in ("", "blue1"):
                match_data[current_match]["rows"].append(
                    {
                        "metric": first,
                        "blue": [str(row.iloc[1]), str(row.iloc[2]), str(row.iloc[3])],
                        "red": [str(row.iloc[5]), str(row.iloc[6]), str(row.iloc[7])],
                    }
                )

        # Build distribution percentiles
        distribution = {}
        for metric, col in [
            ("auto", "auto"),
            ("teleop", "teleop"),
            ("endgame", "endgame"),
            ("total", "score"),
            ("fouls", "foulPoints"),
            ("dpr", "dprs"),
            ("drive", "drive_rank"),
            ("defense", "defense_rank"),
        ]:
            if col in picklist_df.columns:
                vals = pd.to_numeric(picklist_df[col], errors="coerce").dropna()
            elif col in coprs_df.columns:
                vals = pd.to_numeric(coprs_df[col], errors="coerce").dropna()
            elif col in oprs_df.columns:
                vals = pd.to_numeric(oprs_df[col], errors="coerce").dropna()
            else:
                continue
            distribution[metric] = {
                "p25": round(float(vals.quantile(0.25)), 1),
                "p75": round(float(vals.quantile(0.75)), 1),
            }

        match_data["distribution"] = distribution
        push_to_github(match_data, f"webapp/{args.event_key}")

        # Build and push picklist JSON
        picklist_data = {"distribution": distribution, "teams": []}
        for _, row in picklist_df.iterrows():
            picklist_data["teams"].append(
                {
                    "team": int(row["team"]),
                    "score": round(float(row["score"]), 1),
                    "auto": round(float(row["auto"]), 1),
                    "teleop": round(float(row["teleop"]), 1),
                    "endgame": round(float(row["endgame"]), 1),
                    "drive_rank": round(float(row["drive_rank"]), 1) if pd.notna(row["drive_rank"]) else "",
                    "defense_rank": round(float(row["defense_rank"]), 1) if pd.notna(row["defense_rank"]) else "",
                    "breakdown": int(row["breakdown"]) if pd.notna(row["breakdown"]) else 0,
                    "comments": str(row["comments"]) if pd.notna(row["comments"]) else "",
                }
            )

        push_to_github(picklist_data, f"webapp/{args.event_key}_picklist")


if __name__ == "__main__":
    main()
