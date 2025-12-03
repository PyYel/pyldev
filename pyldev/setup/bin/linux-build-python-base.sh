#!/bin/bash

echo "Building the python-base image..."
cd ..

docker build -f "python-base.dockerfile" -t "python-base:latest" .

echo "Program completed. You may close this terminal. If an error arose, see the exception above."

read -p "Press any key to continue... " -n1 -s