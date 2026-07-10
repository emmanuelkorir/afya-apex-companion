# Dockerfile for FastAPI‑Cloud with Prisma client generation
FROM python:3.13-slim

# System deps: gcc for native extensions, libpq-dev for psycopg (PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create an isolated virtual environment so prisma generate targets exactly
# the same Python that will run the application.
RUN python -m venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Install Python dependencies into the venv
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code (local .venv is excluded via .dockerignore)
COPY . .

# Generate the Prisma client — writes into /app/.venv/lib/.../site-packages/prisma/
RUN prisma generate

# Sanity-check: the venv's prisma package should now be importable
RUN python -c "from prisma import Prisma; print('Prisma client OK')"

EXPOSE 8000

# Use sh -c so ${PORT} is evaluated by the shell at runtime
CMD ["sh", "-c", "/app/.venv/bin/uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
