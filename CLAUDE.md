# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Setup (first time):**
```bash
setup.bat        # Creates venv, installs deps, installs pre-commit hooks
```

**Run analysis:**
```bash
run_picklist --event_key <key>                   # Basic run (e.g. 2026ndgf)
run_picklist --event_key <key> --save            # Save event-specific JSON to GitHub
run_picklist --event_key <key> --save --post     # Also update latest_*.json (what webapp reads)
run_picklist --event_key <key> --force           # Re-fetch all cached data
run_picklist --event_key <key> --teams 4607 1234 # Analyze specific teams only
```

**Scheduling during events (Windows):**
```powershell
schedule_picklist.ps1     # Register scheduled task (every 30 min, 9am–7pm)
unschedule_picklist.ps1   # Remove scheduled task
```

**Linting/formatting:**
```bash
ruff format src/          # Format Python
ruff check src/ --fix     # Lint with auto-fix
```
Pre-commit hooks run both automatically on every commit.

## Architecture

This is a Python pipeline that pulls scouting data from multiple sources, blends them into team rankings, and publishes JSON to GitHub where a static webapp reads it.

**Entry point:** `src/scouting_analysis/frc2026_picklist_runner.py` → `main()` (registered as `run_picklist` CLI command in `pyproject.toml`)

### Data Sources

| Module | Source | What it provides |
|--------|--------|-----------------|
| `tba.py` | The Blue Alliance API | Team list, match schedule, match breakdowns, COPR, OPR |
| `sb.py` | Statbotics API | EPA (Expected Points Added) per phase per team |
| `sdb.py` | `api2.lanzersys.com` (4607 internal) | Raw scouting observations, pit data (hopper size) |

All fetched data is cached locally as CSV files and reused on subsequent runs. `--force` bypasses the cache.

### Core Scoring (frc2026_picklist_analysis.py)

`FRC2026PicklistAnalysis` blends data with **dynamic weights** that shift as the event progresses:

```
alpha = played_quals / total_quals          # 0.0 → 1.0 through the event
copr_weight = alpha * 0.75                  # 0% → 75%
epa_weight  = 1.0 - copr_weight            # 100% → 25%

AUTO/TELEOP score  = 10% scouting + copr_weight*COPR + epa_weight*EPA
ENDGAME score      = 50% TBA climb data + 50% EPA endgame
```

This means early in an event the score is EPA-dominated (prediction); late in the event it's COPR-dominated (observed).

### Output & Publishing

The runner generates four JSON files and pushes them to this GitHub repo via REST API:
- `webapp/{event_key}_picklist.json` / `webapp/{event_key}_planner.json` — historical per-event
- `webapp/latest_picklist.json` / `webapp/latest_planner.json` — what the webapp actively reads (`--post` flag)

GitHub Actions (`.github/workflows/notify_slack.yaml`) detects pushes to `webapp/latest_*.json` and sends a Slack notification.

### Webapp

Static HTML/CSS/JS in `webapp/` — no build step. `planner.html` and `picklist.html` fetch JSON from `raw.githubusercontent.com`. Changes to HTML deploy immediately on push.

## Environment

Requires a `.env` file (never committed) with:
```
X-TBA-Auth-Key=<TBA personal API key>
GITHUB_TOKEN=<GitHub PAT with repo write access>
WORKSPACE=<absolute path to project root>
PYTHONPYCACHEPREFIX=C:\Windows\Temp
```

## Key Implementation Details

**CSV parsing in `sdb.py`:** The internal scouting database returns malformed CSV (rows split across lines, extra commas in text fields). The parser explicitly handles both cases: stitching split rows together and truncating over-wide rows at the comments column.

**Climb scoring:** Auto=15pts (any level), Endgame Level1=10/Level2=20/Level3=30pts.

**Prior event COPRs:** For teams with prior events, the runner fetches and averages their previous COPR values as a fallback when current-event data is sparse.

**GitHub push:** Uses the GitHub Contents API (requires fetching the existing file's SHA before updating).

**NaN sanitization:** All floats are sanitized before `json.dumps` because `NaN` is invalid JSON.
