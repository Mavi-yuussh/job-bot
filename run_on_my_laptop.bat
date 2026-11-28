@echo off
REM Double-click: fetch fresh jobs on your own laptop, then open the board.
cd /d %~dp0
python -m pip install -q -r requirements.txt
python jobs_bot.py
start "" http://localhost:8765/docs/index.html
python -m http.server 8765
