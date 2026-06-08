@echo off
echo === PostgreSQL: updating dependencies ===
helm dependency update .

echo === PostgreSQL: installing/upgrading ===
helm upgrade --install postgres . -n default --create-namespace

echo === Done. Check status with: kubectl get pods -n default -l app.kubernetes.io/name=postgresql
