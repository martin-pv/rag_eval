@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 goto RUN_PY
python "%~dp0update-main-sync.py" show %*
goto EOF
:RUN_PY
py -3 "%~dp0update-main-sync.py" show %*
:EOF
