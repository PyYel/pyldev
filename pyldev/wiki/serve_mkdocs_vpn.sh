#!/bin/bash

# Converting the wiki to the mkdocs format
echo "1/6 Converting raw markdown to mkdocs format..."
python raw_to_docs.py

# Install mkdocs and mkdocs-material if not already installed
echo "2/6 Installing mkdocs and mkdocs-material..."
pip install mkdocs mkdocs-material --quiet

# Build the MkDocs site
echo "3/6 Building the mkdocs site..."
mkdocs build

# Retrieve the local IP address
echo "4/6 Retrieving local IP address..."
LOCAL_IP=$(hostname -I | awk '{print $1}')

# Check if the LOCAL_IP variable is set
if [ -z "$LOCAL_IP" ]; then
  echo "Failed to retrieve local IP address."
  exit 1
fi

# Serve the MkDocs site locally
echo "5/6 Serving the mkdocs site on Local Network..."
nohup mkdocs serve --dev-addr=$LOCAL_IP:8000 > /dev/null 2>&1 &

# Pause to keep the script running
echo "6/6 Server is running, close this terminal to stop it."

# Display the local IP address with color
GREEN='\033[0;32m'
NC='\033[0m' # No Color
read -p "\n\t MkDocs server up at ${GREEN}http://$LOCAL_IP:8000/${NC}"