@echo off
setlocal

set IMAGE=pyldev-cdk

echo Running CDK synth using image %IMAGE%

for %%i in ("%~dp0..\..") do set REPO_ROOT=%%~fi

echo Root defined at %REPO_ROOT%
echo Note that only files below this root can be read. 

@REM Bootstrapping the account


docker run --rm ^
  -v "%REPO_ROOT%:/workspace" ^
  -v "%USERPROFILE%\.aws:/root/.aws:ro" ^
  -w /workspace/infrastructure/cdk ^
  --entrypoint sh ^
  --env-file %REPO_ROOT%\infrastructure\.env ^
  %IMAGE% ^
  -c "pip install -r requirements.txt && cdk bootstrap && cdk deploy --all --require-approval never"

echo.
pause