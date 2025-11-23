# Use Python 3.12.9 slim image
FROM python:3.12.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Note: Model files will be downloaded automatically on first run
# Skipping download-files during build to avoid requiring API keys
# The LiveKit agent will download required models when it starts

# Create data directory for SQLite and tokens
RUN mkdir -p data

# Make start script executable
RUN chmod +x start.sh

# Expose port (Cloud Run will override with PORT env var)
EXPOSE 8000

# Run the start script
CMD ["./start.sh"]
