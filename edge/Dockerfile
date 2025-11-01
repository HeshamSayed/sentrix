FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8001

# Run the application with optimal settings for 8-core server
# --workers 8: One worker per CPU core
# --loop uvloop: Faster event loop
# --limit-concurrency 10000: Max concurrent connections per worker
# --backlog 2048: Connection queue size
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "8", "--loop", "uvloop", "--limit-concurrency", "10000", "--backlog", "2048"]

