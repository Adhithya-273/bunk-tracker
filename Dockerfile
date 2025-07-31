FROM debian:bullseye-slim AS builder

# Install system dependencies for Chrome and utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fonts-liberation \
    libu2f-udev \
    unzip \
    wget \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Download and install Google Chrome
RUN wget -q [https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb](https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb) \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb

# Download and install the correct version of ChromeDriver
RUN CHROME_VERSION=$(google-chrome --version | cut -f 3 -d ' ' | cut -d '.' -f 1-3) && \
    DRIVER_URL=$(wget -qO- "[https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json](https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json)" | jq -r ".versions[] | select(.version | startswith(\"${CHROME_VERSION}\")) | .downloads.chromedriver[] | select(.platform==\"linux64\") | .url") && \
    wget -q --continue -P /tmp/ ${DRIVER_URL} && \
    unzip /tmp/chromedriver-linux64.zip -d /opt/

# --- Stage 2: Final Image ---
# This stage builds the final, lightweight image with our Python app
FROM python:3.11-slim-bullseye

# Set the working directory inside the container
WORKDIR /app

# Copy the browser and driver from the builder stage
COPY --from=builder /opt/chromedriver-linux64/chromedriver /usr/bin/chromedriver
COPY --from=builder /opt/google/chrome /opt/google/chrome
COPY --from=builder /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu
COPY --from=builder /lib/x86_64-linux-gnu /lib/x86_64-linux-gnu

# Copy the requirements file and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Set environment variables for Selenium
ENV PATH=/usr/bin:${PATH}

# Expose the port the app will run on
EXPOSE 8080

# Define the command to run the application using gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
