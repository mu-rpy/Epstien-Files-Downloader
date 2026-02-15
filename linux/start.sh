@echo off
setlocal enabledelayedexpansion

if exist "src\data\.setup_done" goto :run_script

:setup
echo [PHASE 1] Checking Python 3.14...
py -3.14 --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Python 3.14.3 not found. Downloading...
    curl.exe -L -o python_installer.exe https://www.python.org/ftp/python/3.14.3/python-3.14.3-amd64.exe
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1
    del python_installer.exe
)

echo [PHASE 2] Installing Playwright ^& Dependencies...
py -3.14 -m pip install --quiet pipenv
cd src
pipenv --python 3.14
pipenv install playwright httpx
pipenv run python -m playwright install chromium
cd ..

echo [PHASE 3] Running Integrity Check...
pipenv run python src/integrity.py
if %errorlevel% neq 0 (
    set /p cont="Integrity failed. Continue? (y/n): "
    if /i "!cont!" neq "y" exit /b 1
)
type nul > src\data\.setup_done

:run_script
cls
set "ver_val=Unknown"
if exist "src\data\version" set /p ver_val=<"src\data\version"
cls
echo [32m
if exist "src\data\logo.txt" type src\data\logo.txt
echo.
echo.
echo [96mAuthor: Mu_rpy[0m
echo [92mVersion: %ver_val%[0m
echo.
echo [0m1. Start PDF Scraper
echo 2. Check for Updates
echo 3. Exit
echo.
set /p menu="Select an option (1-3): "

if "%menu%"=="1" (
    cd src && pipenv run python main.py
    cd ..
    pause
    goto :run_script
)
if "%menu%"=="2" (
    cd src && pipenv run python updater.py
    if %errorlevel% equ 0 exit
    cd ..
    pause
    goto :run_script
)
if "%menu%"=="3" exit /b 0
goto :run_script