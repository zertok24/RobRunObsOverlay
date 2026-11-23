@echo off
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
%PY% --version >nul 2>nul || (
  echo Python est necessaire UNIQUEMENT pour fabriquer l'exe : https://www.python.org/downloads/
  echo Coche "Add python.exe to PATH" a l'installation, puis relance ce fichier.
  pause & exit /b 1
)
%PY% -m pip install --quiet --upgrade pyinstaller || (echo Echec de l'installation de pyinstaller & pause & exit /b 1)
set DATA=--add-data "overlay.html;."
set ICON=
if exist logo.png (
  set DATA=%DATA% --add-data "logo.png;."
  %PY% -m pip install --quiet --upgrade pillow
  %PY% make_icon.py && set ICON=--icon icon.ico
) else (
  echo ATTENTION : logo.png introuvable, l'exe n'aura pas d'icone. Mets logo.png a cote de ce fichier.
)
%PY% -m PyInstaller --onefile --clean --name RobRunObsOverlay %ICON% %DATA% robrun_stats.py || (echo Echec de la fabrication & pause & exit /b 1)
echo.
echo Termine ! Donne le contenu du dossier "dist" a tes potes :
echo   RobRunObsOverlay.exe  (double-clic pour lancer, tout se gere dans sa fenetre)
pause
