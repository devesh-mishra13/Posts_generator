FROM python:3.11.5

# Install dependencies
RUN apt-get update && apt-get install -y \
    chromium chromium-driver wget unzip curl gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Chromium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . /app
WORKDIR /app

# Expose Streamlit default port
EXPOSE 8501

# Run your app
CMD ["streamlit", "run", "app.py"]
