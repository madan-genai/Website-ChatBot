FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
# install-deps ko suppress karo — hum manually handle karenge
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

WORKDIR /app

# Debian Trixie compatible Chromium dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core
    ca-certificates \
    curl \
    wget \
    # Chromium runtime deps
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2t64 \
    libxshmfence1 \
    libglib2.0-0 \
    # Fonts — Debian Trixie correct names
    fonts-liberation \
    fonts-unifont \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --upgrade pip --root-user-action=ignore && \
    pip install --no-cache-dir -r requirements.txt --root-user-action=ignore

# install-deps skip — manually handled above
RUN playwright install chromium

# User setup
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app && \
    chown -R appuser:appgroup /ms-playwright

COPY . .

RUN mkdir -p /app/data && \
    chown -R appuser:appgroup /app/data

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]