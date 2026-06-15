@echo off
:: Force the current directory to be the project root (where this script is located)
cd /d "%~dp0"

set PYTHONPATH=%~dp0src
set HFORCH_DEVICE=cpu

echo ----------------------------------------------------------------
echo CLEAN & UPDATE ORCHESTRTOR
echo ----------------------------------------------------------------
echo Working Directory: %CD%
echo Target Database:   %CD%\db\hf_models.db
echo ----------------------------------------------------------------

echo.
echo [1/2] Cleaning up old database files...
if exist "db\hf_models.db" (
    del /f /q "db\hf_models.db"
    echo   - Deleted hf_models.db
)
if exist "db\hf_models.db-journal" (
    del /f /q "db\hf_models.db-journal"
    echo   - Deleted hf_models.db-journal
)

echo.
echo [2/2] Starting fresh update process...
echo   - This processes ~2 million models.
echo   - It may take several hours.
echo   - Do NOT close this window.
echo.

:: Run the update
python -m hforchestra.main --update

echo.
echo Process complete.
pause
