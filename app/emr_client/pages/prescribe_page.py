import re
from playwright.sync_api import Playwright, sync_playwright, expect

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    # 1. Navigate to your application
    page.goto("YOUR_APPLICATION_URL")

    # Helper function to handle Telerik RadComboBoxes
    def select_telerik_dropdown(input_id, item_text):
        # The arrow usually has the same ID base but ends in _Arrow
        arrow_id = input_id.replace("_Input", "_Arrow")
        page.click(f"#{arrow_id}")
        # Telerik items are often rendered in a global list at the end of the body
        # We look for a list item that contains the exact text
        page.locator("li", has_text=re.compile(f"^{item_text}$")).click()

    
    ## ctl00_ContentPlaceHolder1_RadWindow1 this is the iframe containing the prescription form

    # 2. Fill the Form Fields
    # Dose (Text Input)
    page.fill("#ctl00_ContentPlaceHolder1_txtDose", "80")

    # Unit (Dropdown)
    select_telerik_dropdown("ctl00_ContentPlaceHolder1_ddlUnit_Input", "mg")

    # Frequency (Dropdown)
    select_telerik_dropdown("ctl00_ContentPlaceHolder1_ddlFrequencyId_Input", "2 times a day")

    # Duration (Text Input)
    page.fill("#ctl00_ContentPlaceHolder1_txtDuration", "7")

    # Period Type (Dropdown - defaults to Day(s))
    # select_telerik_dropdown("ctl00_ContentPlaceHolder1_ddlPeriodType_Input", "Day(s)")

    # Route (Dropdown)
    select_telerik_dropdown("ctl00_ContentPlaceHolder1_ddlRoute_Input", "Subcutaneous")

    # Start Date (Date Input)
    page.fill("#ctl00_ContentPlaceHolder1_txtStartDate_dateInput", "2026-07-10")

    # 3. Add to List
    # The button has a specific ID. We use click, or we can use the keyboard shortcut.
    add_button = page.locator("#ctl00_ContentPlaceHolder1_btnAddItem")
    add_button.click()
    
    # Alternatively, use the shortcut defined in the UI (Ctrl+F7)
    # page.keyboard.press("Control+F7")

    # 4. Optional: Verify success
    # expect(page.get_by_text("Drug added successfully")).to_be_visible()

    # Keep browser open for a moment to see results
    page.wait_for_timeout(3000)
    
    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)