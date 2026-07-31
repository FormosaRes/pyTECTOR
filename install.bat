@echo off
REM ---------------------------------------------------------------------------
REM pyTECTOR one-click setup for Windows.
REM
REM Run it from the unpacked pyTECTOR folder. It does the whole job:
REM
REM   1. finds a Python: Anaconda or Miniconda first, then PATH, then the py
REM      launcher. The Microsoft Store stub is skipped on purpose; it is not a
REM      real interpreter and PyQt5 does not work under it.
REM   2. if the machine has no Python at all, offers to download Miniconda
REM      from repo.anaconda.com and install it for this user only.
REM   3. installs numpy, scipy, matplotlib and PyQt5, falling back to
REM      conda-forge for anything pip cannot supply.
REM   4. checks that all four actually import, rather than trusting pip's
REM      exit code.
REM   5. records the interpreter it used in python-path.txt, so pyTECTOR.bat
REM      starts that same one and not some other python on PATH.
REM   6. compile-checks the program and puts a shortcut on the desktop.
REM
REM Safe to run twice. Needs no administrator rights.
REM
REM Kept pure ASCII on purpose: batch files with non-ASCII comments break on
REM machines whose OEM codepage differs from the author's.
REM ---------------------------------------------------------------------------
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title pyTECTOR setup

set "MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
set "DOWNLOAD_PAGE=https://www.anaconda.com/download/success"
set "PYEXE="
set "CONDA="
set "MISSING="

echo.
echo   pyTECTOR setup
echo   ==============
echo.

REM --- 1. find an interpreter -------------------------------------------------
echo [1/5] Looking for a Python interpreter ...

REM An interpreter named by hand wins over everything, then conda, then what a
REM previous run recorded. conda comes before the recorded path on purpose: a
REM second run of this script is usually someone who has just installed
REM Anaconda to fix a broken setup, and it should pick that up rather than go
REM stubbornly back to the interpreter that was not working.
if defined PYTECTOR_PYTHON call :try_python "%PYTECTOR_PYTHON%"

for %%d in (
    "C:\ANACONDA"
    "%USERPROFILE%\anaconda3"
    "%USERPROFILE%\miniconda3"
    "%LOCALAPPDATA%\anaconda3"
    "%LOCALAPPDATA%\miniconda3"
    "%LOCALAPPDATA%\Continuum\anaconda3"
    "%ProgramData%\anaconda3"
    "%ProgramData%\miniconda3"
    "C:\Anaconda3"
    "C:\Miniconda3"
) do call :try_python "%%~d\python.exe"

if not defined PYEXE if exist "python-path.txt" (
    for /f "usebackq delims=" %%p in ("python-path.txt") do call :try_python "%%p"
)

if not defined PYEXE (
    for /f "delims=" %%p in ('where python 2^>nul') do call :try_python "%%p"
)

if not defined PYEXE (
    py -3 -c "import sys; print(sys.executable)" >"%TEMP%\pytector_py.txt" 2>nul
    if exist "%TEMP%\pytector_py.txt" (
        for /f "usebackq delims=" %%p in ("%TEMP%\pytector_py.txt") do call :try_python "%%p"
        del "%TEMP%\pytector_py.txt" >nul 2>&1
    )
)

if defined PYEXE goto have_python

REM --- 1b. no Python: offer to install Miniconda -------------------------------
echo.
echo   No Python was found on this machine.
echo.
echo   pyTECTOR needs one. The recommended choice is Miniconda: a small Python
echo   distribution that installs into a folder of its own, needs no
echo   administrator rights, and brings the conda package manager, which
echo   supplies scipy and Qt as prebuilt binaries instead of compiling them.
echo.
echo   This script can fetch and install it for you, from the official site:
echo     %MINICONDA_URL%
echo   About 80 MB. A couple of minutes. Installed for this user only, and
echo   nothing else on the machine is changed.
echo.
set "ANS="
set /p "ANS=  Download and install Miniconda now? [Y/n] "
if /i "!ANS!"=="n"  goto no_python
if /i "!ANS!"=="no" goto no_python
call :install_miniconda
if not defined PYEXE goto no_python

:have_python
echo       Using: %PYEXE%
call :find_conda
if defined CONDA echo       conda: %CONDA%

REM --- 2. dependencies --------------------------------------------------------
echo.
echo [2/5] Installing numpy, scipy, matplotlib and PyQt5 ...
echo.
"%PYEXE%" -m pip install --upgrade pip >nul 2>&1
"%PYEXE%" -m pip install -r requirements.txt

REM --- 3. verify --------------------------------------------------------------
echo.
echo [3/5] Checking that all four import ...
call :collect_missing
if not defined MISSING goto deps_ok

echo       pip did not supply:!MISSING!
if not defined CONDA goto deps_failed

echo       Trying conda-forge instead ...
echo.
call "%CONDA%" install -y -c conda-forge !MISSING!
echo.
set "MISSING="
call :collect_missing
if not defined MISSING goto deps_ok

:deps_failed
echo.
echo   Setup could not install:!MISSING!
echo.
echo   If this machine is offline, that is the reason: all four packages are
echo   downloaded, not bundled. On a machine with a network, the usual cause
echo   is a proxy blocking pip. Install them by hand and run install.bat again:
echo.
echo       "%PYEXE%" -m pip install numpy scipy matplotlib PyQt5
echo.
pause
exit /b 1

:deps_ok
echo       numpy, scipy, matplotlib and PyQt5 all import.

REM --- 4. record the interpreter and compile-check -----------------------------
>"python-path.txt" echo %PYEXE%

echo.
echo [4/5] Checking that the program compiles ...
"%PYEXE%" -m py_compile pyTECTOR.py
if errorlevel 1 (
    echo       Compile check failed. The download may be incomplete: fetch the
    echo       repository again rather than patching this copy.
    pause
    exit /b 1
)
echo       pyTECTOR.py compiles.

REM --- 5. desktop shortcut ----------------------------------------------------
echo.
echo [5/5] Creating a desktop shortcut ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop') + '\pyTECTOR.lnk');" ^
  "$s.TargetPath = '%~dp0pyTECTOR.bat';" ^
  "$s.WorkingDirectory = '%~dp0';" ^
  "$s.Description = 'Angelier palaeostress inversion';" ^
  "$s.Save()"
if errorlevel 1 (
    echo       Could not create the shortcut. Start the program with pyTECTOR.bat
    echo       in this folder instead.
) else (
    echo       Done.
)

echo.
echo   pyTECTOR is installed. Double-click pyTECTOR on the desktop to start.
echo.
pause
endlocal
exit /b 0


REM ============================================================================
REM  Subroutines
REM ============================================================================

REM --- try_python "<path or command>" -----------------------------------------
REM Accepts the candidate only if it runs and is Python 3.8 or newer, then
REM normalises it to sys.executable so python-path.txt always holds a full path.
:try_python
if defined PYEXE goto :eof
set "CAND=%~1"
if "%CAND%"=="" goto :eof
REM The Store alias is a stub that opens the Microsoft Store. It answers
REM --version convincingly enough to fool a naive check, so exclude it by path.
if not "%CAND%"=="%CAND:WindowsApps=%" goto :eof
"%CAND%" -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if errorlevel 1 goto :eof
"%CAND%" -c "import sys; print(sys.executable)" >"%TEMP%\pytector_which.txt" 2>nul
for /f "usebackq delims=" %%e in ("%TEMP%\pytector_which.txt") do set "PYEXE=%%e"
del "%TEMP%\pytector_which.txt" >nul 2>&1
if not defined PYEXE set "PYEXE=%CAND%"
goto :eof

REM --- find_conda -------------------------------------------------------------
REM Looks for conda beside the chosen interpreter rather than on PATH, so that
REM a conda from some other installation is never used against this one.
:find_conda
for %%p in ("%PYEXE%") do set "PYDIR=%%~dpp"
if exist "%PYDIR%Scripts\conda.exe" set "CONDA=%PYDIR%Scripts\conda.exe"
if not defined CONDA if exist "%PYDIR%condabin\conda.bat" set "CONDA=%PYDIR%condabin\conda.bat"
goto :eof

REM --- collect_missing --------------------------------------------------------
REM pip can report success and still leave a package unusable, so ask Python.
:collect_missing
call :need numpy      numpy
call :need scipy      scipy
call :need matplotlib matplotlib
call :need PyQt5.QtWidgets pyqt
goto :eof

REM --- need <module> <conda package name> --------------------------------------
:need
"%PYEXE%" -c "import %~1" >nul 2>&1
if errorlevel 1 set "MISSING=!MISSING! %~2"
goto :eof

REM --- install_miniconda ------------------------------------------------------
:install_miniconda
REM Install prefix chosen for plain ASCII and no spaces. conda and Qt both
REM misbehave under a home directory whose name is not ASCII, which is the
REM normal case on a Chinese or Japanese Windows account, so C:\Miniconda3 is
REM preferred and the user folder is only the fallback.
set "PREFIX=C:\Miniconda3"
mkdir "%PREFIX%" >nul 2>&1
if exist "%PREFIX%\" goto prefix_ok
echo   C:\ is not writable without administrator rights. Installing into your
echo   user folder instead.
set "PREFIX=%LOCALAPPDATA%\Miniconda3"

:prefix_ok
set "DL=%TEMP%\Miniconda3-latest-Windows-x86_64.exe"
echo.
echo   Downloading Miniconda ...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ProgressPreference = 'SilentlyContinue';" ^
  "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12;" ^
  "try { Invoke-WebRequest -Uri '%MINICONDA_URL%' -OutFile '%DL%' -UseBasicParsing } catch { exit 1 }"
if errorlevel 1 goto download_failed
if not exist "%DL%" goto download_failed

echo   Installing Miniconda into !PREFIX! ...
echo   This takes a minute or two and opens no windows.
start /wait "" "%DL%" /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=!PREFIX!
del "%DL%" >nul 2>&1

if not exist "!PREFIX!\python.exe" (
    echo.
    echo   Miniconda did not appear at !PREFIX!.
    goto :eof
)
call :try_python "!PREFIX!\python.exe"
echo   Miniconda installed.
goto :eof

:download_failed
echo.
echo   The download failed. This is usually the network or a proxy.
goto :eof

REM --- no usable Python -------------------------------------------------------
:no_python
echo.
echo   Setup stopped: pyTECTOR has no Python to run on.
echo.
echo   Install Miniconda or Anaconda by hand, then run install.bat again. The
echo   download page is opening in your browser:
echo     %DOWNLOAD_PAGE%
echo.
echo   The installer's own default answers are the right ones. You do not need
echo   to tick "Add to PATH", and you do not need administrator rights.
echo.
start "" "%DOWNLOAD_PAGE%"
pause
exit /b 1
