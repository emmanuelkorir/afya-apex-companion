"""FastAPI route that receives Telegram webhook updates."""

from __future__ import annotations

from fastapi import APIRouter, Request
from telegram import Update
from telegram.ext import Application

router = APIRouter()


def build_telegram_router(application: Application) -> APIRouter:
    @router.post("/telegram/webhook")
    async def telegram_webhook(request: Request) -> dict:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return {"ok": True}

    return router