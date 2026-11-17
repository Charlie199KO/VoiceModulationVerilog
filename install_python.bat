@echo off
setlocal
cd /d "%~dp0"
echo Creating Python virtual environment...
py -3 -m venv .venv
if errorlevel 1 goto :error
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :error
pip install -r python\requirements.txt
if errorlevel 1 goto :error
echo.
echo Python setup complete.
echo To launch: run_app.bat
goto :eof
:error
echo Setup failed. Check that Python 3 is installed and available as py.
exit /b 1
