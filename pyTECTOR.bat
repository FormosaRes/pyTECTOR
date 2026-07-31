@echo off
REM pyTECTOR launcher for Windows.
REM
REM Starts the interpreter install.bat recorded in python-path.txt, so the
REM program runs on the Python the dependencies were installed into rather
REM than on whichever python happens to be first on PATH. Order: an explicit
REM PYTECTOR_PYTHON, then that recorded path, then the usual Anaconda and
REM Miniconda locations, then PATH.
REM
REM Kept pure ASCII on purpose, like install.bat.
setlocal
cd /d "%~dp0"

set "PYEXE="
if defined PYTECTOR_PYTHON set "PYEXE=%PYTECTOR_PYTHON%"

if not defined PYEXE if exist "python-path.txt" (
    for /f "usebackq delims=" %%p in ("python-path.txt") do if exist "%%p" set "PYEXE=%%p"
)

for %%d in (
    "C:\ANACONDA"
    "%USERPROFILE%\anaconda3"
    "%USERPROFILE%\miniconda3"
    "%LOCALAPPDATA%\anaconda3"
    "%LOCALAPPDATA%\miniconda3"
    "%ProgramData%\anaconda3"
    "%ProgramData%\miniconda3"
    "C:\Anaconda3"
    "C:\Miniconda3"
) do if not defined PYEXE if exist "%%~d\python.exe" set "PYEXE=%%~d\python.exe"

if not defined PYEXE set "PYEXE=python"

"%PYEXE%" pyTECTOR.py %*
if errorlevel 1 (
    echo.
    echo pyTECTOR exited with an error. If it says a module is missing, run
    echo install.bat in this folder: it installs the four dependencies and
    echo records which Python to use.
    pause
)
endlocal
