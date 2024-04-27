@REM Workspace
set workspace=%~dp0

@REM Virtual environment
python -m venv %workspace%venv
call %workspace%venv\Scripts\activate.bat

python -m pip install --upgrade pip
python -m pip install --requirement %workspace%requirements.txt
python -m pip install --editable %workspace%

pre-commit install
