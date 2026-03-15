# Activate the venv
& "$PSScriptRoot\venv\Scripts\Activate.ps1"

# Set project-specific history
Set-PSReadLineOption -HistorySavePath "$PSScriptRoot\.ps_history"

# Display available commands
Write-Host "FRC4607 Scouting Analysis loaded!" -ForegroundColor Green
Write-Host "Available commands:" -ForegroundColor Blue
Write-Host "  run_picklist --event_key <event_key> [--save] [--teams <team1> <team2> ...]"