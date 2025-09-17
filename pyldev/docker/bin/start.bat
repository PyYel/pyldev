@echo off
echo "Starting the containers..."

cd ..
docker-compose -f "docker-compose.yml" -p "<docker-stack>" up -d

echo "Container stack started. If an error arose, see the message above."
pause