@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================
echo   Smart Meeting Notes / Weekly Report Agent
echo ============================================
echo.

rem --- 0. make sure we are in the project folder ---
if not exist "%~dp0app.py" (
    echo [ERROR] app.py not found in this folder.
    echo Please run start.bat from inside the project folder:
    echo   %~dp0
    echo.
    pause
    exit /b 1
)

rem --- 1. find a Python that can import streamlit ---
set "PY_EXE="

for %%P in (
    "D:\ancacoda\python.exe"
    "C:\ProgramData\anaconda3\python.exe"
    "C:\ProgramData\miniconda3\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
) do (
    if not defined PY_EXE (
        if exist "%%~P" (
            "%%~P" -c "import streamlit" >nul 2>nul
            if not errorlevel 1 set "PY_EXE=%%~P"
        )
    )
)

if not defined PY_EXE (
    where python >nul 2>nul
    if not errorlevel 1 set "PY_EXE=python"
)

if not defined PY_EXE (
    echo [ERROR] Python not found.
    echo Please install Python 3.10 or newer from https://www.python.org/downloads/
    echo and check "Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [INFO] Python: %PY_EXE%
"%PY_EXE%" --version

rem --- 2. check dependencies, install if missing ---
"%PY_EXE%" -c "import streamlit, pandas, plotly, docx, requests" >nul 2>nul
if errorlevel 1 (
    echo [INFO] First run: installing dependencies, please wait 1-3 min...
    "%PY_EXE%" -m pip install -r "%~dp0requirements.txt"
    if errorlevel 1 (
        echo.
        echo [ERROR] Dependency install failed. Please run manually:
        echo   "%PY_EXE%" -m pip install -r "%~dp0requirements.txt"
        echo.
        pause
        exit /b 1
    )
)

rem --- 3. launch ---
echo.
echo [INFO] Starting... open http://localhost:8501 in your browser.
echo [INFO] Close this window to stop the app.
echo.
"%PY_EXE%" -m streamlit run "%~dp0app.py"

pause
