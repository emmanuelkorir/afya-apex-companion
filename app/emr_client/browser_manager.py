"""Owns the Playwright browser lifecycle. No login logic, no repositories, no settings."""

from __future__ import annotations
from playwright.async_api import Browser, BrowserContext, Playwright, async_playwright


class BrowserManager:
    """Manages a single long-lived Playwright Browser instance.

    Hands out fresh BrowserContexts per caller so each EMR login gets an
    isolated cookie/storage jar. Knows nothing about EMR credentials or
    what a caller does with a context once it has one.
    """

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def start(self) -> None:
        """Start Playwright and launch the browser. Safe to call once at app startup."""
        if self._browser is not None:
            return
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)

    async def new_context(self) -> BrowserContext:
        """Create a fresh, isolated browser context for a single login/session."""
        return await self.browser.new_context()

    async def close(self) -> None:
        """Close the browser and stop Playwright. Call once at app shutdown."""
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    @property
    def browser(self) -> Browser:
        if self._browser is None:
            raise RuntimeError("BrowserManager not started — call start() first")
        return self._browser