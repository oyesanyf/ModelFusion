@echo off
echo Starting HFOrchestra Web UI...
cd /d %~dp0\web_ui
call npm run dev
pause

