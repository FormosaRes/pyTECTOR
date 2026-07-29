@echo off
REM pyTECTOR launcher. Uses the Anaconda interpreter, not system Python:
REM PyQt5 desktop apps misbehave under the Store python on this machine.
setlocal
set PYEXE=C:\ANACONDA\python.exe
if not exist "%PYEXE%" set PYEXE=python
cd /d "%~dp0"
"%PYEXE%" pyTECTOR.py %*
if errorlevel 1 pause
endlocal
