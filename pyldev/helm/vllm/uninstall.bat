@echo off
echo === vLLM GPU: uninstalling ===
helm uninstall vllm -n default

echo.
echo === Optionally delete model cache PVC (WARNING: triggers re-download): ===
echo kubectl delete pvc vllm-model-cache -n default
