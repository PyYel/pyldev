@echo off
echo === Helm release status ===
helm status vllm -n default

echo.
echo === Pods ===
kubectl get pods -n default -l app.kubernetes.io/instance=vllm

echo.
echo === PVCs ===
kubectl get pvc -n default -l app.kubernetes.io/instance=vllm

echo.
echo === Recent logs ===
kubectl logs deployment/vllm-vllm -n default --tail=30
