# Use the base image with Python and dependencies installed
FROM python-base:latest

# Set the working directory in the container
WORKDIR /app

# Copy the rest of the application code into the container
COPY . .


# Ensure the start script has execute permissions
RUN pip install -r requirements.txt --no-cache-dir


CMD ["sh", "-c", "cd app && uvicorn main:app --host 0.0.0.0 --port 8000"]


