# Dockerfile
# This file defines the steps to build a container image for your app.

# Use an official Chrome image as the base to ensure all dependencies are present
FROM zenika/alpine-chrome:123

# Install Python and Pip
USER root
RUN apk add --no-cache python3 py3-pip

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Expose the port the app will run on
EXPOSE 8080

# Define the command to run the application using gunicorn
# Gunicorn is a professional-grade server for Flask apps
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
```text
# requirements.txt
# List of Python packages to install

Flask
selenium
beautifulsoup4
gunicorn
