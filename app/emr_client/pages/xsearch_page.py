import re
from playwright.sync_api import Playwright, sync_playwright, expect

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    # Global default timeout – 60 seconds for slow .NET postbacks
    page.set_default_timeout(60000)

    page.goto("https://emr-hmis.apeiro-digital.com/Login.aspx?ReturnUrl=%2f")
    page.wait_for_load_state("networkidle")  # Ensure login page is fully loaded

    # 1. User Name
    expect(page.get_by_role("textbox", name="User Name")).to_be_visible()
    page.get_by_role("textbox", name="User Name").fill("42157")

    # 2. Password
    expect(page.get_by_role("textbox", name="Password")).to_be_visible()
    page.get_by_role("textbox", name="Password").fill("1234")

    # 3. Login (only once)
    login_btn = page.get_by_role("button", name="Login")
    expect(login_btn).to_be_visible()
    login_btn.click()
    login_btn = page.get_by_role("button", name="Login")
    expect(login_btn).to_be_visible()
    login_btn.click()
    # Wait for post‑login navigation to finish
    page.wait_for_load_state("networkidle")

    # 1. Patient Search after logging in 
    pane = page.locator("#RAD_SLIDING_PANE_TEXT_ctl00_rdpAppList")
    expect(pane).to_be_visible()
    pane.click()

    # 2. Search field
    search = page.locator("input[name=\"ctl00$fp1$txtSearchN\"]")
    expect(search).to_be_visible()
    search.click()
    search.fill("UMR PATIENT NUMBER TO SEARCH ENTERED BY USER ON TELEGRAM")

    # 3. Visit Type dropdown
    visit_input = page.locator("input[name=\"ctl00$fp1$drpVisitType\"]")
    expect(visit_input).to_be_visible()
    visit_input.click()
    # Wait for dropdown list item
    ip_item = page.get_by_text("IP", exact=True)
    expect(ip_item).to_be_visible()
    ip_item.click()

    # 4. Provider dropdown
    provider_input = page.locator("#ctl00_fp1_ddlProvider_Input")
    expect(provider_input).to_be_visible()
    provider_input.click()
    all_item = page.get_by_text("All", exact=True)
    expect(all_item).to_be_visible()
    all_item.click()

    # 5. Date Range dropdown
    range_input = page.locator("#ctl00_fp1_ddlrange_Input")
    expect(range_input).to_be_visible()
    range_input.click()
    select_all = page.get_by_text("Select All", exact=True)
    expect(select_all).to_be_visible()
    select_all.click()

    # 6. Specialization (checkbox dropdown)
    spec_input = page.locator("#ctl00_fp1_radSpecialization_Input")
    expect(spec_input).to_be_visible()
    spec_input.click()
    first_checkbox = page.get_by_role("checkbox").first
    expect(first_checkbox).to_be_visible()
    first_checkbox.check()

    # 7. Appointment Status (checkbox dropdown)
    status_input = page.locator("#ctl00_fp1_ddlAppointmentStatus_Input")
    expect(status_input).to_be_visible()
    status_input.click()
    first_checkbox_status = page.get_by_role("checkbox").first
    expect(first_checkbox_status).to_be_visible()
    first_checkbox_status.check()

    # 8. Ward (checkbox dropdown)
    ward_input = page.locator("input[name=\"ctl00$fp1$ddlWard\"]")
    expect(ward_input).to_be_visible()
    ward_input.click()
    first_ward_checkbox = page.get_by_role("checkbox").first
    expect(first_ward_checkbox).to_be_visible()
    first_ward_checkbox.check()

    # 9. Refresh button (triggers postback)
    refresh_btn = page.get_by_role("button", name="Refresh")
    expect(refresh_btn).to_be_visible()
    refresh_btn.click()
    # Wait for the grid to reload after the postback
    page.wait_for_load_state("networkidle")

    # 10. First patient link
    patient = page.locator("a[id$='_lblName']").first
    expect(patient).to_be_visible()
    patient.click()

    # 11. Wait for patient dashboard
    page.wait_for_url("**/PatientDashboardForDoctor.aspx")
    page.wait_for_load_state("networkidle")

    ## Fill Progress Notes
    page.locator("#ctl00_ContentPlaceHolder1_txtProgressNote").click()
    page.locator("#ctl00_ContentPlaceHolder1_txtProgressNote").fill("THIS IS WHAT USER TYPES ON TELEGRAM TO ADD AS PROGRESS NOTES")
    page.get_by_role("button", name="Save (F3)").click()

    ### Orders and procedures
    page.get_by_role("button", name="Add Orders And Procedures").click()

    # ---------------------
    context.close()
    browser.close()

with sync_playwright() as playwright:
    run(playwright)