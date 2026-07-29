@echo off
REM ---------------------------------------------------------------------------
REM pyTECTOR one-click setup.
REM
REM Installs the four dependencies into whatever Python it finds (Anaconda
REM first, then the python on PATH, then the py launcher), checks the program
REM compiles, and puts a pyTECTOR shortcut on the desktop. Run it from the
REM unpacked pyTECTOR folder. Safe to run twice.
REM
REM Kept pure ASCII on purpose: batch files with non-ASCII comments break on
REM machines whose OEM codepage differs from the author's.
REM ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"

set "PYEXE="
if exist "C:\ANACONDA\python.exe" set "PYEXE=C:\ANACONDA\python.exe"
if not defined PYEXE if exist "%USERPROFILE%\anaconda3\python.exe" set "PYEXE=%USERPROFILE%\anaconda3\python.exe"
if not defined PYEXE (
    where /q python && set "PYEXE=python"
)
if not defined PYEXE (
    where /q py && set "PYEXE=py"
)
if not defined PYEXE (
    echo No Python found. Install Anaconda or Python 3 from python.org,
    echo then run install.bat again.
    pause
    exit /b 1
)

echo Using: %PYEXE%
echo.
echo [1/3] Installing dependencies: numpy scipy matplotlib PyQt5 ...
"%PYEXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo pip failed. If this machine is offline, install Anaconda instead:
    echo it already ships numpy, scipy and matplotlib, and only PyQt5 is
    echo missing:   python -m pip install PyQt5
    pause
    exit /b 1
)

echo.
echo [2/3] Checking that the program compiles ...
"%PYEXE%" -m py_compile pyTECTOR.py
if errorlevel 1 (
    echo Compile check failed. The download may be incomplete.
    pause
    exit /b 1
)

echo.
echo [3/3] Creating a desktop shortcut ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop') + '\pyTECTOR.lnk');" ^
  "$s.TargetPath = '%~dp0pyTECTOR.bat';" ^
  "$s.WorkingDirectory = '%~dp0';" ^
  "$s.Description = 'Angelier palaeostress inversion';" ^
  "$s.Save()"
if errorlevel 1 (
    echo Could not create the shortcut; start the program with pyTECTOR.bat
) else (
    echo Done. Double-click pyTECTOR on the desktop to start.
)
echo.
pause
endlocal
