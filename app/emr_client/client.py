from playwright.async_api import Page

from app.emr_client.browser_manager import BrowserManager


class EMRClient:
    def __init__(self, headless: bool = False):
        self.browser = BrowserManager(headless=headless)

    async def connect(self) -> None:
        """
        Start the browser and authenticate into the EMR.
        """
        await self.browser.start()
        await self.browser.login()

    async def disconnect(self) -> None:
        """
        Close the browser.
        """
        await self.browser.close()

    async def save_session(self, path: str = "storage_state.json") -> None:
        """
        Persist the current authenticated browser state.
        """
        await self.browser.save_storage_state(path)

    @property
    def page(self) -> Page:
        """
        Expose the current Playwright page.
        """
        if self.browser.page is None:
            raise RuntimeError("Browser has not been started.")

        return self.browser.page