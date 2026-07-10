"""
Playwright page automation for the Ward Management "Progress Notes"
RadWindow popup.

Assumes the caller has already opened the patient's context menu
(WardManagementService.select_row) and clicked the "Progress Notes" item
(browser_helpers.click_menu_item) - this module only deals with what
happens inside the popup once it's open: reading the patient banner,
typing into the Telerik rich-text editor, saving, and closing.

Save mechanism (confirmed against the live EMR): Ctrl+F3 only commits the
note if keyboard focus is outside the rich-text editor's iframe when it's
pressed. If focus is still inside the editor, the keystroke is swallowed
by the editor itself and nothing saves. `save()` therefore explicitly
clicks the popup's patient-banner label (outside the editor iframe) before
pressing Ctrl+F3.
"""
from __future__ import annotations

from dataclasses import dataclass

from playwright.async_api import Page

_POPUP_IFRAME_SELECTOR = "iframe[name^='RadWindow']"
_BANNER_LABEL_SELECTOR = "#ctl00_ContentPlaceHolder1_Label7"
_EDITOR_IFRAME_SELECTOR = "iframe[id$='txtWProgressNote_contentIframe']"
_MESSAGE_LABEL_SELECTOR = "#ctl00_ContentPlaceHolder1_lblMessage"
_CLOSE_BUTTON_SELECTOR = "a.rwCloseButton"

_DEFAULT_SAVE_TIMEOUT_MS = 10_000
_DEFAULT_SAVE_POLL_INTERVAL_MS = 500


@dataclass(slots=True, frozen=True)
class SaveResult:
    """Outcome of attempting to save a progress note."""

    success: bool
    message: str = ""


@dataclass(slots=True, frozen=True)
class FailureDiagnostics:
    """Captured evidence when a save doesn't confirm, for debugging /
    showing the doctor what to check manually in the EMR."""

    screenshot_bytes: bytes
    popup_html: str


class ProgressNotesService:
    """Stateless service for interacting with the Progress Notes popup."""

    async def open(self, page: Page) -> None:
        """
        Wait for the Progress Notes RadWindow to appear and be ready.

        Raises:
            playwright.async_api.TimeoutError: If the popup or its patient
                banner never becomes visible.
        """
        popup_locator = page.locator(_POPUP_IFRAME_SELECTOR)
        await popup_locator.wait_for(state="visible", timeout=15000)

        popup_frame = page.frame_locator(_POPUP_IFRAME_SELECTOR)
        banner_label = popup_frame.locator(_BANNER_LABEL_SELECTOR)
        await banner_label.wait_for(state="visible", timeout=15000)

    async def fill_note(self, page: Page, note_text: str) -> None:
        """
        Type note_text into the popup's Telerik rich-text editor.

        Clicks the editor body first so Telerik's JS registers focus before
        filling - matching the manually-verified working sequence.
        """
        popup_frame = page.frame_locator(_POPUP_IFRAME_SELECTOR)
        editor_frame = popup_frame.frame_locator(_EDITOR_IFRAME_SELECTOR)
        editor_body = editor_frame.locator("body")

        await editor_body.wait_for(state="visible", timeout=10000)
        await editor_body.click()
        await editor_body.fill(note_text)

    async def save(
        self,
        page: Page,
        timeout_ms: int = _DEFAULT_SAVE_TIMEOUT_MS,
        poll_interval_ms: int = _DEFAULT_SAVE_POLL_INTERVAL_MS,
    ) -> SaveResult:
        """
        Save the note via Ctrl+F3 and poll for confirmation text.

        Moves focus to the patient-banner label (outside the editor
        iframe) before pressing Ctrl+F3 - required for the save to
        register at all.

        Args:
            page: The Playwright Page.
            timeout_ms: Total time to wait for lblMessage to become
                non-empty before giving up.
            poll_interval_ms: Delay between polls of lblMessage.

        Returns:
            SaveResult(success=True, message=...) if lblMessage populated
            in time. SaveResult(success=False) on timeout - this does NOT
            raise, since an unconfirmed save is an expected, recoverable
            outcome the caller (Telegram handler) presents as a
            retry-or-cancel choice, not a hard error.
        """
        popup_frame = page.frame_locator(_POPUP_IFRAME_SELECTOR)

        # Move focus outside the rich-text editor iframe before saving -
        # required by the EMR, see module docstring.
        banner_label = popup_frame.locator(_BANNER_LABEL_SELECTOR)
        await banner_label.click()

        popup_body = popup_frame.locator("body")
        await popup_body.press("Control+F3")

        message_label = popup_frame.locator(_MESSAGE_LABEL_SELECTOR)
        elapsed_ms = 0
        while elapsed_ms < timeout_ms:
            text = (await message_label.text_content()) or ""
            if text.strip():
                return SaveResult(success=True, message=text.strip())
            await page.wait_for_timeout(poll_interval_ms)
            elapsed_ms += poll_interval_ms

        return SaveResult(success=False, message="")

    async def capture_failure_diagnostics(self, page: Page) -> FailureDiagnostics:
        """
        Capture a screenshot and the popup's inner HTML for debugging an
        unconfirmed save. Does not modify or close the popup - the caller
        (Telegram handler, per user decision) offers retry-or-cancel and
        only close() is called once that choice is made.
        """
        screenshot_bytes = await page.screenshot()

        popup_frame = page.frame_locator(_POPUP_IFRAME_SELECTOR)
        popup_html = await popup_frame.locator("body").inner_html()

        return FailureDiagnostics(
            screenshot_bytes=screenshot_bytes,
            popup_html=popup_html,
        )

    async def close(self, page: Page) -> None:
        """
        Close the Progress Notes popup and wait for it to disappear.

        The close button lives on the parent page (not inside the popup
        iframe); `.last` matches the manually-verified working selector
        when multiple `.rwCloseButton` elements are present in the DOM.
        """
        close_button = page.locator(_CLOSE_BUTTON_SELECTOR).last
        await close_button.click()
        await close_button.wait_for(state="hidden", timeout=5000)