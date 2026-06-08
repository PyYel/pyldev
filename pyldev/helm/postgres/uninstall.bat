@echo off
echo === PostgreSQL: uninstalling ===
helm uninstall postgres -n default

echo === Optionally delete PVC (WARNING: data loss): ===
echo kubectl delete pvc -n default -l app.kubernetes.io/instance=postgres
