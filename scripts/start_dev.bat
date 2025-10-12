@echo off
REM Development environment startup script

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
)

REM Start MongoDB if installed locally
where mongod >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    start "" mongod
)

REM Start the application
python src/main.py
