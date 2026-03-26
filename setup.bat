@echo off
title WorkPulse Setup
echo.
echo  =============================================
echo   WorkPulse — First Time Setup
echo  =============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Python not found. Downloading Python 3.12...
    curl -o python_installer.exe https://www.python.org/ftp/python/3.12.0/python-3.12.0-amd64.exe
    python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 Include_pip=1
    del python_installer.exe
    echo  [+] Python installed.
) else (
    echo  [+] Python found.
)

REM Install dependencies
echo.
echo  Installing dependencies...
pip install -r requirements.txt --quiet
echo  [+] Dependencies installed.

REM Create WorkPulse data folder if not exists
if not exist "%LOCALAPPDATA%\WorkPulse\config.env" (
    mkdir "%LOCALAPPDATA%\WorkPulse" 2>nul
    echo  [+] Created WorkPulse data folder.
)

REM Create desktop shortcut
echo.
echo  Creating desktop shortcut...
set SCRIPT_DIR=%~dp0
set SHORTCUT=%USERPROFILE%\Desktop\WorkPulse.lnk
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%SHORTCUT%');$s.TargetPath='pythonw';$s.Arguments='\"%SCRIPT_DIR%main.py\"';$s.WorkingDirectory='%SCRIPT_DIR%';$s.Save()"
echo  [+] Desktop shortcut created.

REM Add to Windows startup
echo.
echo  Adding to Windows startup...
set STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set STARTUP_SHORTCUT=%STARTUP_DIR%\WorkPulse.lnk
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%STARTUP_SHORTCUT%');$s.TargetPath='pythonw';$s.Arguments='\"%SCRIPT_DIR%main.py\"';$s.WorkingDirectory='%SCRIPT_DIR%';$s.Save()"
echo  [+] WorkPulse will start on Windows login.

echo.
echo  =============================================
echo   Setup complete! Launching WorkPulse...
echo  =============================================
echo.

start pythonw "%SCRIPT_DIR%main.py"
timeout /t 3 >nul
