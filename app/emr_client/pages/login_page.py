import os
from urllib.parse import urljoin

from dotenv import load_dotenv
from playwright.async_api import BrowserContext, Page

from app.config.settings import settings

load_dotenv()


class LoginService():
    def __init__(self) -> None:
        self.base_url = os.environ["BASE_URL"]
        self.login_url = urljoin(self.base_url, "Login.aspx")
        self.username = settings.emr_dummy_user
        self.password = settings.emr_dummy_pass

    async def login(
        self,
        page: Page,
        username: str,
        password: str,
    ) -> None:
            
        """
        Logs into the EMR and saves the authenticated browser state
        inside the provided browser context.
        """
        
        await page.goto(self.login_url, wait_until="load")

        await page.get_by_role("textbox", name="User Name").fill(self.username)
        await page.get_by_role("textbox", name="Password").fill(self.password)

        # IMPORTANT:
        # This system requires the Login button to be pressed twice.
        await page.get_by_role("button", name="Login").click()
        await page.get_by_role("button", name="Login").click()

        await page.wait_for_load_state("networkidle")
        await page.wait_for_url("**/default.aspx**", timeout=30000)

        print("Login successful.")