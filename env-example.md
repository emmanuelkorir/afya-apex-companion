# ---------------------------------------------------------------------------
# Afya Apex Companion — environment configuration
# Copy this file to `.env` and fill in real values.
# Never commit the actual `.env` file.
# ---------------------------------------------------------------------------

# --- PostgreSQL (used by the `db` service and by Prisma) -------------------
POSTGRES_USER=afya_user
POSTGRES_PASSWORD=change_me_before_running
POSTGRES_DB=afya_db

# Full connection string Prisma/FastAPI use.
# Host is "db" when running via docker-compose (service name on the internal
# network). If running the API outside Docker against a local Postgres,
# change "db" to "localhost".
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}

# --- FastAPI / app runtime ---------------------------------------------------
PORT=8000
ENV=development
LOG_LEVEL=info

# --- Telegram bot ------------------------------------------------------------
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_WEBHOOK_URL=https://your-domain.example.com/webhook
TELEGRAM_WEBHOOK_SECRET=change_me

# --- Hospital EMR / Playwright automation ------------------------------------
EMR_BASE_URL=https://your-emr-host.example.com
EMR_USERNAME=
EMR_PASSWORD=
PLAYWRIGHT_HEADLESS=true

# --- Session / auth -----------------------------------------------------------
SESSION_SECRET_KEY=change_me_generate_a_random_value
SESSION_TTL_SECONDS=3600
