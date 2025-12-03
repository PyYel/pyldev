#!/bin/bash

echo "Building the RAGbot image..."
cd ..

docker rmi "RAGbot:latest" -f
docker build -f "RAGbot.dockerfile" -t "RAGbot:latest" .

echo "Program completed. You may close this terminal. If an error arose, see the exception above."

read -p "Press any key to continue... " -n1 -s