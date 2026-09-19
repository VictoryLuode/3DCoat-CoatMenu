@echo off
rem CoatMenu installer - double click.
rem Uses 3DCoat's own Python when present (it is the exact interpreter 3DCoat runs).
setlocal

set "COAT_PY=%USERPROFILE%\Documents\3DCoat\python-3.11.9\python.exe"
set "SCRIPT=%~dp0install.py"

if exist "%COAT_PY%" (
    "%COAT_PY%" "%SCRIPT%" %*
) else (
    where python >nul 2>nul && (
        python "%SCRIPT%" %*
    ) || (
        echo No Python found. Run install.py with any Python 3.8+ interpreter.
    )
)

echo.
pause
endlocal
