@echo off

echo Building the ragbot image...
cd ..

docker rmi "server:latest" -f
docker build -f "server.dockerfile" -t "server:latest" .

echo Program completed. You may close this terminal. If an error araised, see the exception above.


pause