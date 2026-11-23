@echo off
cd /d "%~dp0"
echo Les stats vont etre remises a zero (nouveau wipe).
pause
RobRunObsOverlay.exe --reset
