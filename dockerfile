# Base image (stable, production-ready)
FROM python:3.12-slim

# Prevent Python from writing .pyc files + better logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install system dependencies (Playwright + browser support)
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libfontconfig1 \
    libx11-6 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libatk1.0-0 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcups2 \
    libxss1 \
    libgtk-3-0 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for caching layer optimization)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser
RUN pip install playwright && playwright install chromium

# Copy project files
COPY . .

# Create data folder for SQLite / metadata
RUN mkdir -p data

# Expose FastAPI port
EXPOSE 8000

# Start application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]