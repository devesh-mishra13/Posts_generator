# Use the official Streamlit image as base
FROM python:3.11.5

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl unzip gnupg libnss3 libgconf-2-4 libxss1 \
    fonts-liberation libappindicator3-1 libasound2 xdg-utils \
    libu2f-udev libvulkan1 wget \
    chromium-driver chromium \
    && apt-get clean

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Set working directory
WORKDIR /app

# Copy files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run the app
CMD ["streamlit", "run", "your_script_name.py", "--server.port=10000", "--server.enableCORS=false"]
