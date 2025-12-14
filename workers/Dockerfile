# Multi-stage build for Sentinyl Workers
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    dnsutils \
    whois \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy worker code
COPY workers/ /app/workers/
COPY backend/config.py /app/backend/config.py
COPY backend/__init__.py /app/backend/__init__.py

# Create logs directory
RUN mkdir -p /app/logs

# Create a startup script that runs multiple workers
RUN echo '#!/bin/bash\n\
    python -m workers.typosquat_worker &\n\
    python -m workers.leak_worker &\n\
    wait\n\
    ' > /app/start_workers.sh && chmod +x /app/start_workers.sh

# Run workers
CMD ["/app/start_workers.sh"]
