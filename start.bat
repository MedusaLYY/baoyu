@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
set "PROJECT_DIR="
set "HOST=127.0.0.1"
set "PORT=8081"

if exist "%ROOT%app.py" (
    if exist "%ROOT%templates\" set "PROJECT_DIR=%ROOT%"
)

if not defined PROJECT_DIR (
    for /d %%D in ("%ROOT%*") do (
        if exist "%%~fD\app.py" (
            if exist "%%~fD\templates\" (
                set "PROJECT_DIR=%%~fD"
                goto :found_project
            )
        )
    )
)

:found_project
if not defined PROJECT_DIR (
    echo Could not find a Flask project directory with app.py and templates.
    echo Please run this file from the repository root.
    pause
    exit /b 1
)

echo Project directory: "%PROJECT_DIR%"
cd /d "%PROJECT_DIR%"
if errorlevel 1 goto :fail

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if errorlevel 1 goto :fail
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :fail

set "REQ_FILE="
if exist "%ROOT%requirements.txt" set "REQ_FILE=%ROOT%requirements.txt"
if exist "requirements.txt" set "REQ_FILE=requirements.txt"
if not defined REQ_FILE if exist "requirement.txt" set "REQ_FILE=requirement.txt"

if /I "%SKIP_INSTALL%"=="1" (
    echo Skipping dependency install because SKIP_INSTALL=1.
) else (
    if defined REQ_FILE (
        echo Installing dependencies from "%REQ_FILE%"...
        python -m pip install --upgrade pip
        if errorlevel 1 goto :fail
        python -m pip install -r "%REQ_FILE%"
        if errorlevel 1 goto :fail
    ) else (
        echo No requirements file found. Continuing with the current environment.
    )
)

set "FLASK_APP=app.py"
set "ABALONE_ENGINE=local"

if /I "%START_CHECK_ONLY%"=="1" (
    echo Startup check passed. The app would run at http://%HOST%:%PORT%/login.html
    exit /b 0
)

echo Starting Flask app at http://%HOST%:%PORT%/login.html
start "" "http://%HOST%:%PORT%/login.html"
python app.py
if errorlevel 1 goto :fail

exit /b 0

:fail
echo.
echo Startup failed. Please check the error message above.
pause
exit /b 1
