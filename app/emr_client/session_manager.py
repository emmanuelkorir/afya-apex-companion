"""Drives a fresh EMR login and registers the resulting live page.

Session persistence via storage_state is not viable for this EMR — it
enforces single-session-per-user server-side, so a session cannot be
restored in a new browser context. Instead, the logged-in Page stays
open in LivePageRegistry for the lifetime of the user's bot activity.
"""

from __future__ import annotations

from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.emr_client.browser_manager import BrowserManager
from app.emr_client.exceptions import EMRLoginError
from app.emr_client.live_page_registry import LivePageRegistry
from app.emr_client.pages.login_page import EMRLoginService


class EMRSessionManager:
    """Coordinates a fresh EMR login and hands the resulting live page
    off to the shared LivePageRegistry.
    """

    def __init__(
        self,
        browser_manager: BrowserManager,
        login_service: EMRLoginService,
        registry: LivePageRegistry,
    ) -> None:
        self.browser_manager = browser_manager
        self.login_service = login_service
        self.registry = registry

    async def login(self, user_id: str, emr_username: str, emr_password: str) -> None:
        """Log into the EMR and register the resulting live page for this user.

        Replaces any prior live session for this user_id (old context is
        closed by the registry's register() semantics — see note below).
        """
        # Close out any existing live session first — the EMR only allows
        # one at a time anyway, so holding two open serves no purpose.
        await self.registry.logout(user_id)

        context = await self.browser_manager.new_context()
        page = await context.new_page()

        try:
            await self.login_service.login(page, emr_username, emr_password)
        except PlaywrightTimeoutError as e:
            await context.close()
            raise EMRLoginError(
                f"EMR login timed out or failed for user {user_id}"
            ) from e

        # Give any post-redirect AJAX (session finalization, etc.) a
        # chance to complete before treating the login as fully settled.
        await page.wait_for_load_state("networkidle")

        self.registry.register(user_id, context, page)

    def is_logged_in(self, user_id: str) -> bool:
        return self.registry.is_logged_in(user_id)

    async def logout(self, user_id: str) -> None:
        await self.registry.logout(user_id)