@echo off
rem CoatMenu installer - double click.
rem Runs with 3DCoat's own Python when we can find it: that is the exact
rem interpreter 3DCoat runs, so the extension is exercised against what it gets.
rem 3DCoat's data folder (which holds that Python) is Documents\3DCoat by default
rem but can be almost anywhere - chosen on first run, or Documents redirected into
rem OneDrive - so the usual spots are checked rather than assumed.
setlocal enabledelayedexpansion

set "SCRIPT=%~dp0install.py"
set "COAT_PY="

for %%D in (
    "%USERPROFILE%\Documents"
    "%USERPROFILE%\OneDrive\Documents"
    "%USERPROFILE%\OneDrive - Personal\Documents"
) do (
    if not defined COAT_PY if exist "%%~D\3DCoat\python-3.11.9\python.exe" (
        set "COAT_PY=%%~D\3DCoat\python-3.11.9\python.exe"
    )
)

if defined COAT_PY (
    echo Using 3DCoat's own Python:
    echo   !COAT_PY!
    "!COAT_PY!" "%SCRIPT%" %*
) else (
    where python >nul 2>nul && (
        python "%SCRIPT%" %*
    ) || (
        echo No Python on PATH, and 3DCoat's bundled one was not in the usual places.
        echo Use any Python 3.8+ and point it at your Documents folder:
        echo     python install.py --documents "D:\path\to\Documents"
    )
)

echo.
pause
endlocal
