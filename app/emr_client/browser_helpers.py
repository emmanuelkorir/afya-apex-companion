"""
Small, reusable Playwright helpers extracted from the manual test script.

Telerik's client-side controls are flaky enough (occasional ignored first
click; AJAX loading panels that appear/disappear asynchronously) that every
new menu action was going to reimplement the same retry-loop and
loading-panel-wait pattern. This module gives that pattern one home so
future menu items (branch 12: Allergy, Drug Order, etc.) reuse it instead
of copy-pasting.
"""
from __future__ import annotations

from playwright.async_api import Locator, Page

_DEFAULT_MENU_CLIENT_ID = "ctl00_ContentPlaceHolder1_menuStatus"
_LOADING_PANEL_SELECTOR = ".raDiv, .RadAjaxLoadingPanel"


class ClickRetryExhausted(Exception):
    """Raised when a locator could not be clicked after all retry attempts."""

    def __init__(self, attempts: int):
        super().__init__(f"Click failed after {attempts} attempt(s)")
        self.attempts = attempts


async def click_with_retry(
    locator: Locator,
    attempts: int = 3,
    timeout_ms: int = 3000,
    wait_between_ms: int = 300,
) -> None:
    """
    Click a locator, retrying on failure.

    Telerik controls (e.g. the ward dropdown arrow in wardmanagement_page.py)
    occasionally ignore the first click while a postback is settling. This
    retries with a short pause between attempts rather than failing the
    whole operation on one flaky click.

    Args:
        locator: The Playwright Locator to click.
        attempts: Max number of click attempts (default 3).
        timeout_ms: Per-click timeout passed to Locator.click().
        wait_between_ms: Pause between failed attempts. Not applied after
            the final attempt.

    Raises:
        ClickRetryExhausted: If every attempt fails. The last underlying
            exception is chained via `__cause__` for debugging.
    """
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            await locator.click(timeout=timeout_ms)
            return
        except Exception as exc:  # noqa: BLE001 - deliberately broad, retried
            last_exc = exc
            if attempt < attempts - 1:
                await locator.page.wait_for_timeout(wait_between_ms)

    raise ClickRetryExhausted(attempts) from last_exc


async def click_menu_item(
    page: Page,
    item_text: str,
    menu_client_id: str = _DEFAULT_MENU_CLIENT_ID,
) -> None:
    """
    Click an item in a Telerik RadMenu (the `menuStatus_detached` context
    menu) by its visible text, via the client-side Telerik API.

    Generalizes the original hardcoded "Progress Notes" JS injection so
    other menu items (Allergy, Drug Order, Admission Form, ...) can reuse
    it as their handlers are built out.

    Args:
        page: The Playwright Page with the menu currently open.
        item_text: Exact visible text of the menu item, e.g. "Progress Notes".
        menu_client_id: The Telerik RadMenu client ID (default matches the
            ward-management context menu; other menus elsewhere in the EMR
            could pass a different id).

    Raises:
        ValueError: If item_text contains a character that would break out
            of the JS string literal it's interpolated into (double quote
            or backslash). Our own menu list is fixed text, but this is a
            cheap guard against a future caller passing user-derived text.
        Exception: Whatever Page.add_script_tag raises (e.g. a CSP block),
            propagated unchanged so the caller can decide how to surface it.
    """
    if '"' in item_text:
        raise ValueError(f"item_text must not contain a double quote: {item_text!r}")
    if "\\" in item_text:
        raise ValueError(f"item_text must not contain a backslash: {item_text!r}")

    script = f"""
        var menu = $find("{menu_client_id}");
        if (menu) {{
            var item = menu.findItemByText("{item_text}");
            if (item) {{
                if (!item.get_attributes().getAttribute("rmDisabled") && item.get_enabled()) {{
                    // setTimeout breaks out of any restrictive execution context
                    setTimeout(function() {{ item.click(); }}, 10);
                }}
            }}
        }}
    """

    await page.add_script_tag(content=script)

    await page.wait_for_timeout(500)
    loading_panel = page.locator(_LOADING_PANEL_SELECTOR).first
    if await loading_panel.is_visible():
        await loading_panel.wait_for(state="hidden", timeout=15000)