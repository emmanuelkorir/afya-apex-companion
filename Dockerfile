# Minimal Dockerfile for FastAPI‑Cloud (includes Prisma client generation)
# Base image – same Python version you use locally
FROM python:3.13-slim

# Install system packages required by Prisma (gcc) and any DB driver you need (e.g., libpq for PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies – copy lock files first for layer caching
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source code
COPY . .

# Generate Prisma client (must run after dependencies are installed)
RUN prisma generate

# Expose the port FastAPI‑Cloud will bind to (default $PORT, fallback 8000)
EXPOSE 8000

# Default command – FastAPI‑Cloud will replace ${PORT} with the runtime env var
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT}"]
