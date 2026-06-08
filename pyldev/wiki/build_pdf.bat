@echo off
SETLOCAL EnableExtensions

echo ===================================================
echo [1/3] Verifying Docker is running...
echo ===================================================
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo ===================================================
echo [2/3] Building Multi-Stage Docker Image...
echo ===================================================
docker build -t mkdocs-pdf-runner .

if %errorlevel% neq 0 (
    echo [ERROR] Docker image build failed. Check the errors above.
    pause
    exit /b 1
)

echo ===================================================
echo [3/3] Generating PDF (Isolated Sandbox Engine)...
echo ===================================================
:: -v "%cd%:/docs:ro"  -> Mounts your local folder to /docs as Read-Only (Safe)
:: -v "%cd%:/output"    -> Mounts your local root folder to accept the final PDF file
docker run --rm ^
  -v "%cd%:/docs:ro" ^
  -v "%cd%:/output" ^
  mkdocs-pdf-runner

if %errorlevel% neq 0 (
    echo [ERROR] PDF generation failed.
    pause
    exit /b 1
)

echo ===================================================
echo Success! document.pdf is ready at your project root.
echo ===================================================
pause
ENDLOCAL