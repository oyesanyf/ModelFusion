@echo off
:: Set PYTHONPATH to include the src directory
set PYTHONPATH=%~dp0src

:: Run the update command from the project root (where this script is)
python -m hforchestra.main --update

pause
