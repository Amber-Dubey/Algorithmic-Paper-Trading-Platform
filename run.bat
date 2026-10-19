@echo off
CLS
echo ===================================================
echo   Starting Algorithmic Paper Trading Terminal...
echo ===================================================

:: 1. Check if Python is installed and meets the 3.10+ requirement
python --version >nul 2>&1
if errorlevel 1 goto PROMPT_INSTALL

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 goto PROMPT_INSTALL

goto SETUP_VENV

:PROMPT_INSTALL
echo.
echo [NOTICE] Compatible Python (3.10 or higher) was not found.
set /p choice="Would you like to automatically install Python 3.11 now? (Y/N): "
if /i "%choice%"=="Y" (
    echo [INSTALLING] Downloading and installing Python 3.11...
    winget install -e --id Python.Python.3.11 --accept-source-agreements --accept-package-agreements
    echo.
    echo [IMPORTANT] Python installation complete! 
    echo Please CLOSE this command window, open a fresh terminal, 
    echo and double-click 'run.bat' again so your system can recognize it.
    pause
    exit /b
) else (
    echo [EXIT] Python 3.10+ is required to run this app. Exiting.
    pause
    exit /b
)

:SETUP_VENV
:: 2. Check if the venv folder exists; if not, create it
if not exist venv (
    echo [SETUP] Virtual environment not found. Creating 'venv'...
    python -m venv venv
)

:: 3. Activate venv and install requirements
echo [SETUP] Activating virtual environment...
call venv\Scripts\activate.bat

echo [SETUP] Ensuring all requirements are up-to-date...
pip install -r requirements.txt --quiet

:: 4. Launch the application
echo ===================================================
echo   Launching Streamlit Dashboard...
echo ===================================================
streamlit run app.py

pause