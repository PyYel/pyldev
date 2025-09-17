@echo off
setlocal
echo "Building images locally for x86_64 architecture..."

cd ..

docker build -f "Dockerfile" -t "<image>:latest" .

docker image prune -f

echo "Local build completed successfully. If an error araised, see the exception above."

pause