@echo off

echo Stopping and removing existing containers...
for /f "tokens=*" %%i in ('docker ps -a -q --filter "ancestor=server:latest"') do (
    docker stop %%i
    docker rm %%i
)

echo Removing existing images...
docker rmi "server:latest" -f

echo Updating the docker server image...
cd ..

docker build -f "server.dockerfile" -t "server:latest" .

echo Starting the client...
docker-compose -f "docker-compose-server.yml" -p "server" up -d

echo Program completed. You may close this terminal. If an error arose, see the exception above.

pause