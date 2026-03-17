@echo off
set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"
set "PYINSTALLER_RESET_ENVIRONMENT=1"
set "_MEIPASS2="
echo CVRP Optimizer - Starting...
echo.

REM Проверяваме дали има входен файл
if exist "%APP_DIR%data\input.xlsx" (
    echo Input file found: %APP_DIR%data\input.xlsx
    "%APP_DIR%CVRP_Optimizer.exe" "%APP_DIR%data\input.xlsx"
) else (
    echo Input file not found in data\input.xlsx
    echo Place the input file in data\input.xlsx
    echo or in the current directory as input.xlsx
    echo.
    echo Starting with current configuration...
    "%APP_DIR%CVRP_Optimizer.exe"
)
