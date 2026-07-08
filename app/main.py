from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.dependencies import startup, shutdown, telegram_application
from app.bot.router import build_telegram_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup()
    yield
    await shutdown()


app = FastAPI(lifespan=lifespan)
app.include_router(build_telegram_router(telegram_application))