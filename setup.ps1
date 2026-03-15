# Workspace
$workspace = $PSScriptRoot

# Virtual environment
python -m venv "$workspace\venv"
& "$workspace\activate.ps1"
python -m pip install --upgrade pip
python -m pip install --requirement "$workspace\requirements.txt"
python -m pip install --editable "$workspace"
pre-commit install