@echo off

:: Converting the wiki to the mkdocs format
echo 1/6 Converting raw markdown to mkdocs format...
python raw_to_docs.py

:: Install mkdocs and mkdocs-material if not already installed
echo 2/6 Installing mkdocs and mkdocs-material...
pip install mkdocs mkdocs-material --quiet >nul 2>&1

:: Build the MkDocs site
echo 3/6 Building the mkdocs site...
mkdocs build >nul 2>&1

:: Retrieve the local IP address
echo 4/6 Retrieving local IP address...
for /f "tokens=1" %%i in ('powershell -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -ne 'Loopback Pseudo-Interface 1' }).IPAddress"') do set LOCAL_IP=%%i

:: Check if the LOCAL_IP variable is set
if "%LOCAL_IP%"=="" (
    echo Failed to retrieve local IP address.
    pause
    exit /b 1
)

:: Serve the MkDocs site locally
echo 5/6 Serving the mkdocs site on Local Host...
start /B "" cmd /c "mkdocs serve >nul 2>&1"

echo 6/6 Server is running, close this terminal to stop it.

:: Display the local IP address with color
echo.
powershell -Command "Write-Host 'MkDocs server up at http://127.0.0.1:8000/' -ForegroundColor Green"
echo.

