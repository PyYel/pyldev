@echo off

echo Starting the namespace/image container...
cd ..
docker-compose -f "docker-compose.yml" -p "image" up -d

echo Program completed. You may close this terminal. If an error arose, see the exception above.

pause