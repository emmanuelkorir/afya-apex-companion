import asyncio
from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from app.emr_client.pages.login_page import LoginService

from app.config.settings import settings

class BrowserManager:
    def __init__(self, headless: bool = False):
        self.headless = headless

        self._playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

        self.login_service = LoginService()

    async def start(self) -> None:
        """Start Playwright and launch the browser."""

        self._playwright = await async_playwright().start()

        self.browser = await self._playwright.chromium.launch(
            headless=self.headless
        )

        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def login(self) -> None:
        """Authenticate into the EMR."""

        if self.page is None:
            raise RuntimeError("Browser has not been started.")

        await self.login_service.login(self.page, settings.emr_dummy_user,
    settings.emr_dummy_pass,)

    async def save_storage_state(self, path: str = "storage_state.json") -> None:
        """Save authenticated browser session."""

        if self.context is None:
            raise RuntimeError("Browser has not been started.")

        await self.context.storage_state(path=path)

    async def close(self) -> None:
        """Close browser and Playwright."""

        if self.context:
            await self.context.close()

        if self.browser:
            await self.browser.close()

        if self._playwright:
            await self._playwright.stop()