"""Coordinates browser automation, EMR login, and session persistence."""

from __future__ import annotations
from datetime import UTC, datetime, timedelta
from typing import cast

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from prisma.models import EMRSession

from app.database.repositories.session import SessionRepository
from app.emr_client.browser_manager import BrowserManager
from app.emr_client.pages.login_page import EMRLoginService
from app.emr_client.exceptions import EMRLoginError

_SESSION_TTL = timedelta(hours=8)


class EMRSessionManager:
    """Drives a fresh EMR login and persists the resulting storage_state.

    This is the single point of contact for anything EMR-session-related.
    Callers outside app/emr_client should never import SessionRepository,
    BrowserManager, or EMRLoginService directly.
    """

    def __init__(
        self,
        browser_manager: BrowserManager,
        login_service: EMRLoginService,
        sessions: SessionRepository,
    ) -> None:
        self.browser_manager = browser_manager
        self.login_service = login_service
        self.sessions = sessions

    async def login_and_persist(
        self,
        user_id: str,
        emr_username: str,
        emr_password: str,
    ) -> EMRSession:
        """Log into the EMR with the given credentials and persist the
        resulting session.
        """
        context = await self.browser_manager.new_context()
        try:
            page = await context.new_page()
            try:
                await self.login_service.login(page, emr_username, emr_password)
            except PlaywrightTimeoutError as e:
                raise EMRLoginError(
                    f"EMR login timed out or failed for user {user_id}"
                ) from e

            storage_state = cast("dict", await context.storage_state())
        finally:
            await context.close()

        expires_at = datetime.now(UTC) + _SESSION_TTL
        return await self.sessions.create_session(
            user_id=user_id,
            storage_state=storage_state,
            expires_at=expires_at,
        )

    async def get_active_session(self, user_id: str) -> EMRSession | None:
        """Return the user's current active EMR session, if any.

        Passthrough to SessionRepository — kept here so callers outside
        emr_client never need to know SessionRepository exists.
        """
        return await self.sessions.get_active_session(user_id)