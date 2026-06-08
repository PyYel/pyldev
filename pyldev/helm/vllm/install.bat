@echo off
echo === WARNING: This chart requires a GPU node. Do NOT run on a CPU-only machine. ===
echo === Use vllm-cpu\install.bat for local k3d development. ===
echo.
set /p CONFIRM=Type YES to proceed anyway: 
if /i "%CONFIRM%" NEQ "YES" (
  echo Aborted.
  exit /b 1
)

echo === vLLM GPU: installing/upgrading ===
helm upgrade --install vllm . -n default --create-namespace

echo.
echo === Pods ===
kubectl get pods -n default -l app.kubernetes.io/name=vllm
