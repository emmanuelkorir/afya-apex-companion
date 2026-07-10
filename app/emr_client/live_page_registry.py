"""Registry of live, logged-in Playwright pages, keyed by user_id.

Because this EMR enforces single-session-per-user server-side, a login
session cannot be persisted to a database and replayed later in a fresh
browser context — the server ties the session to the actual live
connection that logged in. So instead of persisting storage_state, we
keep the logged-in Page/BrowserContext alive in memory for as long as
the user is actively using the bot, and every subsequent action (search,
labs, prescriptions, notes) reuses this exact same Page.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from playwright.async_api import BrowserContext, Page

from app.emr_client.exceptions import NoActiveEMRSession

# How long a live session may sit idle (no action taken) before it's
# considered stale and swept. Reset on every touch().
_IDLE_TTL = timedelta(minutes=15)


@dataclass
class _LiveSession:
    context: BrowserContext
    page: Page
    last_used: datetime = field(default_factory=lambda: datetime.now(UTC))


class LivePageRegistry:
    """In-memory registry of one live logged-in Page per user_id.

    Not persisted — if the process restarts, all live sessions are lost
    and users must /start again to log in. This is expected given the
    EMR's single-session enforcement; there is no durable alternative.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, _LiveSession] = {}

    def register(self, user_id: str, context: BrowserContext, page: Page) -> None:
        """Register a freshly logged-in page for a user, replacing any prior one."""
        self._sessions[user_id] = _LiveSession(context=context, page=page)

    def get_page(self, user_id: str) -> Page:
        """Return the user's live page, touching its idle timer.

        Raises NoActiveEMRSession if there's no live session, or it's
        gone stale past the idle TTL.
        """
        session = self._sessions.get(user_id)
        if session is None:
            raise NoActiveEMRSession(f"No live EMR session for user {user_id}")

        if datetime.now(UTC) - session.last_used > _IDLE_TTL:
            raise NoActiveEMRSession(f"Live EMR session for user {user_id} has gone idle")

        session.last_used = datetime.now(UTC)
        return session.page

    def is_logged_in(self, user_id: str) -> bool:
        """Check without raising — used for the requires_login flag."""
        session = self._sessions.get(user_id)
        if session is None:
            return False
        return datetime.now(UTC) - session.last_used <= _IDLE_TTL

    async def logout(self, user_id: str) -> None:
        """Close and remove a user's live session, if any."""
        session = self._sessions.pop(user_id, None)
        if session is not None:
            await session.context.close()

    async def sweep_expired(self) -> None:
        """Close any live sessions past their idle TTL. Call periodically
        (e.g. a background task) — not wired up automatically yet.
        """
        now = datetime.now(UTC)
        expired = [
            uid for uid, s in self._sessions.items()
            if now - s.last_used > _IDLE_TTL
        ]
        for uid in expired:
            await self.logout(uid)