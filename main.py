# main.py – FastAPI entry point at repository root
"""
Root‑level FastAPI entry point.
Keeps the same startup/shutdown logic that was previously in app/main.py,
but lives at the repository root so Railway can run `uvicorn main:app`.
"""

import sys
import asyncio
import os

# Windows Proactor event loop is required for Playwright subprocess support
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# -------------------------------------------------
# Import your internal FastAPI helpers – adjust if your package layout differs
# -------------------------------------------------
from contextlib import asynccontextmanager

from fastapi import FastAPI

# These imports assume the existing package structure under the `app/` directory
from app.dependencies import startup, shutdown, telegram_application
from app.bot.router import build_telegram_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup / shutdown code around the FastAPI life‑cycle."""
    await startup()
    yield
    await shutdown()


# Create the FastAPI instance with the custom lifespan handler
app = FastAPI(lifespan=lifespan)

# Attach any routers – e.g., the Telegram router you already have
app.include_router(build_telegram_router(telegram_application))


# -------------------------------------------------
# When executed directly (local development) we honour the $PORT env var
# -------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,
    )
