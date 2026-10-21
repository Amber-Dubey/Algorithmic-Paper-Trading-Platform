@echo off
CLS
echo ===================================================
echo   Starting Algorithmic Paper Trading Terminal...
echo ===================================================

:: Force check for modern Python via Windows launcher (py)
py -3.13 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.13"
    goto CHECK_VERSION
)

py -3.11 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.11"
    goto CHECK_VERSION
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    goto CHECK_VERSION ::devloper: Amber Dubey
)

:: Fallback check
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto CHECK_VERSION
)

echo [ERROR] Compatible Python (3.10 or higher) not found.
pause
exit /b

:CHECK_VERSION
:: Verify the detected version is at least 3.10
%PYTHON_CMD% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo [ERROR] The detected Python version is below 3.10.
    pause
    exit /b
)

:: Setup venv using the modern Python command
if not exist venv (
    echo [SETUP] Creating virtual environment using modern Python...
    %PYTHON_CMD% -m venv venv
)

:: Activate venv and install requirements
echo [SETUP] Activating virtual environment...
call venv\Scripts\activate.bat

echo [SETUP] Installing requirements...
pip install -r requirements.txt --quiet

:: Launch application
echo ===================================================
echo   Launching Streamlit Dashboard...
echo ===================================================
streamlit run app.py

pause