#!/bin/bash

echo "Updating the docker RAGbot image..."
cd ..

docker rmi "RAGbot:latest" -f
docker build -f "RAGbot.dockerfile" -t "RAGbot:latest"  .

echo "Starting the RAGbot server..."
docker-compose -f "docker-compose-server.yml" -p "server" up

echo "Program completed. You may close this terminal. If an error arose, see the exception above."

read -p "Press any key to continue... " -n1 -s