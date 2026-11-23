@echo off
REM Starts the dashboard on Windows. First run creates the virtual environment.
cd /d "%~dp0"
if not exist .venv (
    echo Creating virtual environment...
    py -3 -m venv .venv || goto :error
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt || goto :error
) else (
    call .venv\Scripts\activate.bat
)
if not exist .env (
    echo No .env file found. Copy .env.example to .env and fill in your printer details.
    pause
    exit /b 1
)
python -m app
goto :eof

:error
echo Setup failed. See the message above.
pause
exit /b 1
