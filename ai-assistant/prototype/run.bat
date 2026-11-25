@echo off
cd /d "%~dp0"
echo Starting Kit Assistant on http://localhost:8000 ...
start "" http://localhost:8000
python server.py
