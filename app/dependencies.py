"""Composition root: wires up repositories, services, and shared singletons."""

from __future__ import annotations

from app.database.prisma import Database
from app.database.repositories.user import UserRepository
from app.database.repositories.session import SessionRepository
from app.emr_client.browser_manager import BrowserManager
from app.emr_client.pages.login_page import EMRLoginService
from app.emr_client.session_manager import EMRSessionManager
from app.auth.service import SessionAuthenticationService
from app.bot.bot import build_application

database = Database()

browser_manager = BrowserManager(headless=True)
login_service = EMRLoginService()

user_repository = UserRepository(database)
session_repository = SessionRepository(database)

emr_session_manager = EMRSessionManager(
    browser_manager=browser_manager,
    login_service=login_service,
    sessions=session_repository,
)

auth_service = SessionAuthenticationService(
    users=user_repository,
    emr=emr_session_manager,
)

telegram_application = build_application(auth_service)


async def startup() -> None:
    await database.connect()
    await browser_manager.start()
    await telegram_application.initialize()
    await telegram_application.start()


async def shutdown() -> None:
    await telegram_application.stop()
    await telegram_application.shutdown()
    await browser_manager.close()
    await database.disconnect()


def get_auth_service() -> SessionAuthenticationService:
    return auth_service