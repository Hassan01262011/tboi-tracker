@echo off
cd /d "%~dp0"
TBOISyncHelper.exe --install
if errorlevel 1 pause
