@echo off
setlocal

REM project directory
set PROJECT_DIR=%cd%

REM image name
set IMAGE=pyldev-cdk

REM check if image already exists
docker image inspect %IMAGE% >nul 2>nul
if %errorlevel% neq 0 (
    echo Local CDK image not found. Building it...

    REM create Dockerfile dynamically
    (
    echo FROM node:20-alpine
    
    echo RUN npm install -g aws-cdk
    echo RUN apk add --no-cache python3 py3-pip
    echo WORKDIR /workspace

    echo ENV PIP_BREAK_SYSTEM_PACKAGES=1
    echo RUN pip3 install aws-cdk-lib constructs
    ) > Dockerfile.cdk

    echo Building local CDK image...

    docker build -t %IMAGE% -f Dockerfile.cdk . && (
        echo Image build succeeded.
    ) || (
        echo Image build FAILED.
        pause
        exit /b 1
    )

    DEL Dockerfile.cdk
)

echo Running CDK synth using image %IMAGE%...

for %%i in ("%~dp0..\..") do set REPO_ROOT=%%~fi
echo %REPO_ROOT%
docker run --rm ^
  -v "%REPO_ROOT%:/workspace" ^
  -w /workspace/infrastructure/cdk ^
  --entrypoint sh ^
  --env-file %REPO_ROOT%/infrastructure/.env ^
  %IMAGE% ^
  -c "pip install -r requirements.txt && cdk synth"

echo.
echo CDK output generated in: %PROJECT_DIR%/cdk.out

endlocal
pause