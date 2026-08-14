@echo off
title Persona 5 Royal — Web Save Editor
echo ========================================================
echo   PERSONA 5 ROYAL // PHANTOM SAVE EDITOR WEB APP
echo ========================================================
echo.
echo Launching local server at http://127.0.0.1:5055 ...
start http://127.0.0.1:5055
python "%~dp0server.py"
pause
