@echo off
title WorkPulse Build
echo.
echo  Building WorkPulse.exe...
echo.

pyinstaller ^
  --name WorkPulse ^
  --onefile ^
  --windowed ^
  --add-data "data;data" ^
  --add-data "sounds;sounds" ^
  --add-data "assets;assets" ^
  --hidden-import PyQt6.QtCore ^
  --hidden-import PyQt6.QtGui ^
  --hidden-import PyQt6.QtWidgets ^
  main.py

echo.
echo  Build complete. Output: dist\WorkPulse.exe
pause
