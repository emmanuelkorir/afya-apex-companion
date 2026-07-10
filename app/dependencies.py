"""Composition root: wires up repositories, services, and shared singletons."""

from __future__ import annotations

from app.database.prisma import Database
from app.database.repositories.user import UserRepository
from app.database.repositories.session import SessionRepository
from app.emr_client.live_page_registry import LivePageRegistry
from app.emr_client.browser_manager import BrowserManager
from app.emr_client.pages.login_page import EMRLoginService
from app.emr_client.session_manager import EMRSessionManager
from app.emr_client.pages.search_page import SearchService
from app.emr_client.search_manager import SearchSessionManager
from app.emr_client.pages.wardmanagement_page import WardManagementService
from app.emr_client.pages.progress_notes_page import ProgressNotesService
from app.emr_client.ward_manager import WardSessionManager
from app.auth.service import SessionAuthenticationService
from app.bot.bot import build_application

database = Database()

browser_manager = BrowserManager(headless=True)
login_service = EMRLoginService()

user_repository = UserRepository(database)
session_repository = SessionRepository(database)
registry = LivePageRegistry()

emr_session_manager = EMRSessionManager(
    browser_manager=browser_manager,
    login_service=login_service,
    registry=registry,
)

auth_service = SessionAuthenticationService(
    users=user_repository,
    emr=emr_session_manager,
)

search_service = SearchService()
search_session_manager = SearchSessionManager(
    registry=registry,
    search_service=search_service,
)

ward_service = WardManagementService()
progress_notes_service = ProgressNotesService()
ward_session_manager = WardSessionManager(
    registry=registry,
    ward_service=ward_service,
    progress_notes_service=progress_notes_service,
)

telegram_application = build_application(auth_service, search_session_manager, ward_session_manager)


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