# Stage 1: Install Chrome and ChromeDriver
FROM debian:bullseye-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fonts-liberation \
    libu2f-udev \
    unzip \
    wget \
    jq \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update && apt-get install -y --no-install-recommends ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb

RUN CHROME_VERSION=$(google-chrome --version | cut -f 3 -d ' ' | cut -d '.' -f 1-3) && \
    DRIVER_URL=$(wget -qO- "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json" | jq -r ".versions[] | select(.version | startswith(\"${CHROME_VERSION}\")) | .downloads.chromedriver[] | select(.platform==\"linux64\") | .url") && \
    wget -q --continue -P /tmp/ ${DRIVER_URL} && \
    unzip /tmp/chromedriver-linux64.zip -d /opt/ && \
    chmod +x /opt/chromedriver-linux64/chromedriver

# Stage 2: Final image
FROM python:3.11-slim-bullseye

WORKDIR /app

COPY --from=builder /opt/chromedriver-linux64/chromedriver /usr/bin/chromedriver
COPY --from=builder /opt/google/chrome /opt/google/chrome
COPY --from=builder /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu
COPY --from=builder /lib/x86_64-linux-gnu /lib/x86_64-linux-gnu

ENV CHROME_BIN=/opt/google/chrome/google-chrome
ENV PATH="/usr/bin:${PATH}"

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
