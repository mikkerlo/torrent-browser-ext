# server/Dockerfile
# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
# Assumes requirements.txt is in the same directory as the Dockerfile (the server directory)
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code from the server directory to the working directory
COPY . .

# Environment variables that will be available to app.py
# Flask app settings (FLASK_APP should point to the app factory)
ENV FLASK_APP=app:create_app 
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=5000

# qBittorrent connection details (override these with your actual values)
ENV QB_URL="http://localhost:8080/"
ENV QB_USER="admin"
ENV QB_PASS="adminadmin"

# Flask Secret Key (CHANGE THIS IN YOUR ENVIRONMENT)
ENV FLASK_SECRET_KEY="your_default_very_secret_key_here_CHANGE_ME"

# Application users (username:password,comma-separated)
ENV APP_USERS=""

# CORS Origins (comma-separated list of allowed origins for browser extension)
ENV CORS_ORIGINS="*"

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Command to run the application using Gunicorn as WSGI server
# Gunicorn will look for a callable named create_app in a module named app (app.py)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:create_app()"]
