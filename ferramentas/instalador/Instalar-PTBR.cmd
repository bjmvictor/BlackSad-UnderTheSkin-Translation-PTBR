@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Instalar-PTBR.ps1"
if errorlevel 1 pause
