# ---------- Build stage ----------
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY prisma ./prisma
COPY . .

# Generate once here with a dummy URL just to cache the engine binary download.
RUN DATABASE_URL="postgresql://dummy:dummy@localhost:5432/dummy" \
    python -m prisma generate || true

# ---------- Runtime stage ----------
FROM python:3.12-slim AS runtime

# Playwright needs its runtime libs even without the build toolchain.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 appuser
WORKDIR /app

COPY --from=builder /root/.local /home/appuser/.local
COPY --from=builder /app /app

RUN playwright install chromium --with-deps \
    && chown -R appuser:appuser /app /home/appuser/.local

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

CMD ["make", "run"]