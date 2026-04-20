@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

cd ..

:: Check if .env file exists
if not exist .env (
    echo [ERROR] .env file not found!
    exit /b 1
)

:: Load variables from .env
echo [INFO] Loading environment variables from .env...
for /f "usebackq tokens=1,2 delims==" %%A in (".env") do (

    :: TF var expansion
    set "TF_VAR_%%A=%%B"
    
    :: Duplicate for non-tf var compatibility
    set "%%A=%%B"
    
    echo   - Loaded: %%A = %%B
)

cd tf

echo [INFO] Executing: terraform init -backend-config="bucket=%TF_STATE_BUCKET%"
terraform init -backend-config="bucket=%TF_STATE_BUCKET%"

echo [INFO] Backing up terraform state to:
terraform state pull > terraform.tfstate

@REM echo [INFO] Executing: terraform plan
@REM terraform plan

ENDLOCAL
pause