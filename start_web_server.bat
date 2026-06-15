@echo off
echo Starting HFOrchestra Web API Server...
cd /d %~dp0
python -m uvicorn web_api.server:app --reload --host 0.0.0.0 --port 8000
pause

