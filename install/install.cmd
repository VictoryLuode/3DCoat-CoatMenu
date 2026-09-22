@echo off
rem CoatMenu installer - double click.
rem
rem Runs with 3DCoat's own Python when it can find it: that is the exact
rem interpreter 3DCoat runs, so the extension is exercised against what it gets.
rem
rem 3DCoat keeps that Python inside its *data* folder, as python-<version>, and
rem both halves of that path move around: the data folder can be anywhere (it is
rem chosen on first run), Documents itself is often redirected into OneDrive or
rem onto another drive, and the version in the folder name changes when 3DCoat
rem updates. So: the registry is asked for Documents first, the usual places come
rem after, any python-* folder is accepted, and a candidate has to actually run
rem before it is used. Python 3.8+ is the only requirement - the installer needs
rem nothing else (no PySide6, no pip).
setlocal enabledelayedexpansion

set "SCRIPT=%~dp0install.py"
set "COAT_PY="
set "PY_CMD="

rem --- the Documents folder Windows itself knows about ------------------------
rem (User Shell Folders may still hold %USERPROFILE%; one extra expansion.)
set "DOCS="
for /f "tokens=2,*" %%A in ('reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" /v Personal 2^>nul ^| findstr /i "Personal"') do set "DOCS=%%B"
if defined DOCS call set "DOCS=%DOCS%"

rem --- 3DCoat's own Python: any python-* folder inside its data folder ---------
for %%R in ("!DOCS!" "%USERPROFILE%\Documents" "%USERPROFILE%\OneDrive\Documents" "%USERPROFILE%\OneDrive - Personal\Documents") do (
    if not "%%~R"=="" (
        for /d %%P in ("%%~R\3DCoat\python-*") do (
            if not defined COAT_PY if exist "%%~P\python.exe" (
                "%%~P\python.exe" -c "import sys" >nul 2>nul
                if not errorlevel 1 set "COAT_PY=%%~P\python.exe"
            )
        )
    )
)

if defined COAT_PY (
    echo Using 3DCoat's own Python:
    echo   !COAT_PY!
    "!COAT_PY!" "%SCRIPT%" %*
    goto :done
)

rem --- the py launcher, then whatever "python" is on PATH ---------------------
rem A candidate has to run before it is used: the Windows Store stub for
rem python.exe sits on PATH on most machines, and running it opens the Store
rem instead of doing anything - which looks exactly like a broken installer.
py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"

if not defined PY_CMD (
    for /f "delims=" %%P in ('where python 2^>nul') do (
        if not defined PY_CMD (
            echo "%%~P" | findstr /i "WindowsApps" >nul
            if errorlevel 1 (
                "%%~P" -c "import sys" >nul 2>nul
                if not errorlevel 1 set "PY_CMD=%%~P"
            )
        )
    )
)

if defined PY_CMD (
    echo Using the Python on this machine:
    echo   !PY_CMD!
    !PY_CMD! "%SCRIPT%" %*
    goto :done
)

echo No Python found.
echo   3DCoat's own one was not under Documents\3DCoat either, so do one of:
echo     - start 3DCoat once (it unpacks its Python into its data folder), or
echo     - install Python 3.8+ from python.org, or
echo     - run the installer by hand with any Python 3.8+:
echo         python install.py --documents "D:\path\to\Documents"

:done
echo.
pause
endlocal
