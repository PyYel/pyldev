@echo off

echo "Building images locally for x86_64 architecture..."
cd ..

docker build -f "Dockerfile" -t "namespace/image:latest" .

docker image prune -f

echo Program completed. You may close this terminal. If an error araised, see the exception above.


pause