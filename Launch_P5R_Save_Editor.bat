@echo off
setlocal
cd /d "%~dp0"
title Persona 5 Royal Save Editor

if exist "dist\P5R_Save_Editor\P5R_Save_Editor.exe" (
    start "" "dist\P5R_Save_Editor\P5R_Save_Editor.exe"
) else if exist "P5R_Save_Editor.exe" (
    start "" "P5R_Save_Editor.exe"
) else (
    echo Starting Persona 5 Royal Save Editor via Python...
    python main.py
)
endlocal
