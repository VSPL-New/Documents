@echo off
REM Quick Start Script for GitHub Issues Import (Windows)

echo ==================================================
echo   ValueX User Stories to GitHub Issues Importer
echo ==================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.7+
    pause
    exit /b 1
)
echo [OK] Python found

REM Check if config exists
if not exist "config.json" (
    echo.
    echo Warning: config.json not found
    echo.
    set /p CREATE="Would you like to create it from template? (y/n): "
    if /i "%CREATE%"=="y" (
        copy config.example.json config.json
        echo [OK] Created config.json
        echo.
        echo Please edit config.json with your details:
        echo    - github_token: Your GitHub Personal Access Token
        echo    - repo_owner: Your GitHub username or organization
        echo    - repo_name: Your repository name
        echo.
        pause
    ) else (
        echo Error: Cannot proceed without config.json
        pause
        exit /b 1
    )
)

REM Install dependencies
echo.
echo Installing dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM Verify user stories file
if not exist "..\Documents\user-stories.md" (
    echo Error: User stories file not found
    pause
    exit /b 1
)
echo [OK] User stories file found

REM Dry run test
echo.
echo Running test (dry run with first 5 stories)...
echo.
python import_user_stories_to_github.py --dry-run --story-range 1-5

echo.
echo ==================================================
echo   Ready to import!
echo ==================================================
echo.
echo What would you like to do?
echo.
echo   1. Import MVP Core stories (US-001 to US-057)
echo   2. Import all stories (US-001 to US-100)
echo   3. Import specific range
echo   4. Exit (import manually later)
echo.
set /p CHOICE="Choose option (1-4): "

if "%CHOICE%"=="1" (
    echo.
    echo Importing MVP Core stories...
    python import_user_stories_to_github.py --story-range 1-57
) else if "%CHOICE%"=="2" (
    echo.
    echo Importing all stories...
    python import_user_stories_to_github.py
) else if "%CHOICE%"=="3" (
    set /p RANGE="Enter range (e.g., 1-10): "
    echo.
    echo Importing stories %RANGE%...
    python import_user_stories_to_github.py --story-range %RANGE%
) else if "%CHOICE%"=="4" (
    echo.
    echo Exiting. Run the script manually when ready.
    pause
    exit /b 0
) else (
    echo.
    echo Error: Invalid option
    pause
    exit /b 1
)

echo.
echo [OK] Import complete!
echo Check your GitHub repository for issues
pause
