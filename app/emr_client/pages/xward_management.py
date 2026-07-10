from playwright.async_api import async_playwright, expect
import asyncio


async def wait_for_telerik(page):
    """Wait for ASP.NET AJAX/Telerik to finish processing."""
    await page.wait_for_load_state("domcontentloaded")

    await page.wait_for_function("""
    () => {
        if (!window.Sys) return true;
        return !Sys.WebForms.PageRequestManager
            .getInstance()
            .get_isInAsyncPostBack();
    }
    """)


async def run():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Login
        await page.goto(
            "https://emr-hmis.apeiro-digital.com/Login.aspx?ReturnUrl=%2f"
        )

        await page.get_by_role("textbox", name="User Name").fill("42157")
        await page.get_by_role("textbox", name="Password").fill("1234")

        login_button = page.get_by_role("button", name="Login")

        # First click
        await login_button.click()

        # Wait for any ASP.NET/Telerik processing
        await wait_for_telerik(page)

        # Second click (required by this EMR)
        await login_button.click()

        # Wait until login completes
        await wait_for_telerik(page)

        # Wait for a post-login element to appear
        await expect(
            page.locator("#RAD_SLIDING_PANE_TEXT_ctl00_rsp1")
        ).to_be_visible(timeout=30000)

        # Navigate
        await page.locator("#RAD_SLIDING_PANE_TEXT_ctl00_rsp1").click()
        await page.get_by_role("link", name="Ward Management").click()

        await wait_for_telerik(page)

        # Open Telerik RadComboBox
        arrow = page.locator("#ctl00_ContentPlaceHolder1_ddlName_Arrow")

        await expect(arrow).to_be_visible(timeout=10000)
        await expect(arrow).to_be_enabled()

        await arrow.scroll_into_view_if_needed()

        # Retry because Telerik occasionally ignores the first click
        for _ in range(3):
            try:
                await arrow.click(timeout=3000)
                break
            except Exception:
                await page.wait_for_timeout(300)

        dropdown = page.locator("#ctl00_ContentPlaceHolder1_ddlName_DropDown")
        await dropdown.wait_for(state="visible", timeout=10000)

        await dropdown.get_by_text("UMR", exact=True).click()

        await wait_for_telerik(page)

        # Search patient
        await page.locator("#ctl00_ContentPlaceHolder1_txtSearchContent").fill("1552093")
        await page.get_by_role("button", name="Filter").click()
        await wait_for_telerik(page)

        patient_cell = page.locator("td[onclick*='showMenu']")
        await patient_cell.wait_for(state="visible", timeout=10000)
        await patient_cell.scroll_into_view_if_needed()
        await patient_cell.click()

        print("Patient cell clicked")

        context_menu = page.locator("#ctl00_ContentPlaceHolder1_menuStatus_detached")
        await context_menu.wait_for(state="visible", timeout=10000)

        # ## 'Progress Notes' SHOULD be DYNAMIC THERE SHOULD BE OPTIONS to do other tasks based on the detached menu status, 

        js_script = """
            var menu = $find("ctl00_ContentPlaceHolder1_menuStatus");
            if (menu) {
                var item = menu.findItemByText("Progress Notes");
                if (item) {
                    if (!item.get_attributes().getAttribute("rmDisabled") && item.get_enabled()) {
                        // setTimeout breaks out of any restrictive execution context
                        setTimeout(function() { item.click(); }, 10);
                    }
                }
            }
        """

        try:
            # add_script_tag adds the script to the HTML <head> and runs it natively
            await page.add_script_tag(content=js_script)
            print("Telerik API Click executed natively.")
        except Exception as e:
            print(f"Failed to inject script: {str(e)}")
            await page.screenshot(path="failed_script_injection.png", full_page=True)
            raise e
        print("Waiting for AJAX postback to complete...")
        loading_panel = page.locator(".raDiv, .RadAjaxLoadingPanel").first
        await page.wait_for_timeout(500)
        if await loading_panel.is_visible():
            await loading_panel.wait_for(state="hidden", timeout=15000)

        # 4. Now wait for the RadWindow iframe to appear
        print("Waiting for RadWindow iframe...")
        popup_frame = page.frame_locator("iframe[name^='RadWindow']")
        popup_locator = page.locator("iframe[name^='RadWindow']")
        
        # Ensure the popup is attached to the DOM and visible
        await popup_locator.wait_for(state="visible", timeout=15000)
        
        print("RadWindow (Progress Notes) opened successfully.")

        progress_note_label = popup_frame.locator("#ctl00_ContentPlaceHolder1_Label7")
        await progress_note_label.wait_for(state="visible", timeout=15000)

        # 5. LOCATE AND FILL THE INNER TEXT EDITOR
        print("Locating Telerik Rich Text Editor...")
        editor_iframe = popup_frame.frame_locator("iframe[id$='txtWProgressNote_contentIframe']")
        editor_body = editor_iframe.locator("body")
        
        await editor_body.wait_for(state="visible", timeout=10000)
        
        # Click it to ensure Telerik's Javascript registers focus
        await editor_body.click()
        await page.wait_for_timeout(500) # Brief pause for focus to settle

        # The placeholder text from Telegram
        note_text = "DWR: Patient is stable. Continue current treatment plan. Monitor vitals every 4 hours. Next review in 24 hours."
        print(f"Typing note: {note_text}")
        
        # Type the text into the iframe
        await editor_body.fill(note_text)

        # 6. SAVE LOGIC (Currently commented out for testing)
        print("Pressing Ctrl + F3 to save... (Simulated)")
        
        # WHEN READY, UNCOMMENT THESE:
        # await popup_frame.locator("body").press("Control+F3")
        # message_label = popup_frame.locator("#ctl00_ContentPlaceHolder1_lblMessage")
        # await expect(message_label).not_to_be_empty(timeout=10000)
        # print("Save confirmed.")

        # Just wait a couple of seconds so you can visually confirm the text was typed
        await page.wait_for_timeout(2000)

        # 7. CLOSE THE WINDOW
        print("Closing the Progress Note window...")
        # Telerik close button is on the parent page, not inside the iframe
        close_button = page.locator("a.rwCloseButton").last
        await close_button.click()

        # Verify it closed
        await expect(close_button).to_be_hidden(timeout=5000)
        print("Progress note window closed successfully.")

        await page.pause()
    
        await context.close()
        await browser.close()


asyncio.run(run())
