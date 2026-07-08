"""Playwright page automation for the Apex EMR login flow."""

from __future__ import annotations
from urllib.parse import urljoin

from playwright.async_api import Page

from app.config.settings import settings


class EMRLoginService:
    """Drives the EMR login form. Pure page automation — no browser/context
    lifecycle, no stored credentials, no persistence.
    """

    def __init__(self) -> None:
        self.base_url = settings.base_url
        self.login_url = urljoin(self.base_url, "Login.aspx")

    async def login(self, page: Page, username: str, password: str) -> None:
        """Log into the EMR using the given credentials.

        Does not return or persist anything — caller is responsible for
        extracting `context.storage_state()` after this succeeds.
        """
        await page.goto(self.login_url, wait_until="load")

        await page.get_by_role("textbox", name="User Name").fill(username)
        await page.get_by_role("textbox", name="Password").fill(password)

        # IMPORTANT: this system requires the Login button pressed twice.
        await page.get_by_role("button", name="Login").click()
        await page.get_by_role("button", name="Login").click()

        await page.wait_for_load_state("networkidle")
        await page.wait_for_url("**/default.aspx**", timeout=30000)