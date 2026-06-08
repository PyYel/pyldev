@echo off
echo === Helm release status ===
helm status postgres -n default

echo.
echo === Pods ===
kubectl get pods -n default -l app.kubernetes.io/instance=postgres

echo.
echo === PVCs ===
kubectl get pvc -n default -l app.kubernetes.io/instance=postgres
