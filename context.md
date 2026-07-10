Afya Apex Companion is a Telegram bot that gives healthcare professionals secure, conversational access to the Afya Apex Electronic Medical Records system. It automates the browser-based EMR using Playwright, manages user sessions, and exposes key clinical workflows through simple chat commands.

# Project Structure

- **`bot/`** – Telegram bot implementation, command handlers, and message processing.
- **`api/`** – FastAPI backend, including authentication, business logic, and
- user services.
- **`browser/`** – Playwright scripts for automating the Afya Apex EM

# File Structure

- run.py – Entry point for running the bot and backend API.
- app:
  - auth/: service.py, schemas.py, exceptions.py, contracts.py
  - bot/: bot.py, router.py
  - config/: settings.py
  - database/: repositories/, prisma.py, migrations.py, exceptions.py, dependencies.py
    - repositories/: user_repository.py, session_repository.py
  - emr_client/:
    - pages/:
      - login_page.py
      - wardmanagement_page.py
    - browser_manager.py
    - live_page_registry.py
    - ward_manager.py
    - session_manager.py
  - dependencies.py for fastapi dependency injection
  - main.py

# Codebase

search_page.py
"""Playwright page automation for EMR patient search."""

from **future** import annotations
from dataclasses import dataclass

from playwright.async_api import Page

# Telerik/ASP.NET AJAX postbacks can be slow; give generous timeouts

# rather than the Playwright default of 30s.

\_ELEMENT_TIMEOUT_MS = 60_000

@dataclass(slots=True)
class PatientSearchResult:
row_index: int
umr: str
visit_no: str
name: str
age_gender: str
ward: str

class SearchService:
\_MAX_RESULTS = 5

    async def search_by_umr(self, page: Page, umr: str) -> list[PatientSearchResult]:
        # Ensure any in-flight AJAX/postback from the prior page load has
        # settled before we start looking for elements.

        await page.wait_for_load_state("networkidle")

        pane = page.locator("#RAD_SLIDING_PANE_TEXT_ctl00_rdpAppList")

        await pane.wait_for(state="visible", timeout=_ELEMENT_TIMEOUT_MS)

        await pane.click()

        search = page.locator('input[name="ctl00$fp1$txtSearchN"]')
        await search.wait_for(state="visible", timeout=_ELEMENT_TIMEOUT_MS)
        await search.click()
        await search.fill(umr)

        visit_input = page.locator('input[name="ctl00$fp1$drpVisitType"]')
        await visit_input.click()
        await page.get_by_text("IP", exact=True).click()

        # provider_input = page.locator("#ctl00_fp1_ddlProvider_Input")
        # await provider_input.click()
        # await page.get_by_text("All", exact=True).click()

        provider_input = page.locator("#ctl00_fp1_ddlProvider_Input")

        await provider_input.wait_for(state="visible", timeout=_ELEMENT_TIMEOUT_MS)

        await provider_input.click()

        await provider_input.press("Control+A")  # Select all text

        await provider_input.press("Delete")

        await provider_input.type("All", delay=100)

        await provider_input.press("Enter")


        await page.get_by_role("button", name="Refresh").click()

        await page.wait_for_load_state("networkidle", timeout=_ELEMENT_TIMEOUT_MS)

        return await self._extract_results(page)

    # ... _extract_results, total_result_count, select_row unchanged ...

    async def _extract_results(self, page: Page) -> list[PatientSearchResult]:
        rows = page.locator(
            "table[id*='gvEncounter'] tr.rgRow, table[id*='gvEncounter'] tr.rgAltRow"
        )
        count = await rows.count()

        results: list[PatientSearchResult] = []
        for i in range(min(count, self._MAX_RESULTS)):
            row = rows.nth(i)
            umr = await row.locator("[id$='_lblRegistrationNo']").inner_text()
            visit_no = await row.locator("[id$='_lblEncounterNo']").inner_text()
            name = await row.locator("[id$='_lblName']").inner_text()
            age_gender = await row.locator("[id$='_lblAgeGender']").inner_text()
            ward = await row.locator("[id$='_lblBedNo']").inner_text()

            results.append(
                PatientSearchResult(
                    row_index=i,
                    umr=umr.strip(),
                    visit_no=visit_no.strip(),
                    name=name.strip(),
                    age_gender=age_gender.strip(),
                    ward=ward.strip(),
                )
            )
        return results

    async def total_result_count(self, page: Page) -> int:
        """Return the full grid row count, even beyond the 5 we extract —
        used to tell the user "Showing 5 of N, please narrow your search."
        """
        rows = page.locator(
            "table[id*='gvEncounter'] tr.rgRow, table[id*='gvEncounter'] tr.rgAltRow"
        )
        return await rows.count()

    async def select_row(self, page: Page, row_index: int) -> None:
        """Click the 'Select' link for a given row and wait for the
        patient dashboard to load.
        """
        rows = page.locator(
            "table[id*='gvEncounter'] tr.rgRow, table[id*='gvEncounter'] tr.rgAltRow"
        )
        row = rows.nth(row_index)
        await row.locator("[id$='_lnkSelect']").click()

        await page.wait_for_url("**/PatientDashboardForDoctor.aspx")
        await page.wait_for_load_state("networkidle")

<div class="RadMenu RadMenu_Metro RadMenu_Context RadMenu_Metro_Context    " id="ctl00_ContentPlaceHolder1_menuStatus_detached" style="display: block; visibility: visible; z-index: 7000; overflow: visible; height: 300px; width: 175px; left: 111px; top: 14px;">
		<div class="rmScrollWrap rmGroup rmLevel1" style="width: 175px; height: 300px; overflow: hidden; display: block; top: 0px; visibility: visible;">
			<ul class="rmActive rmVertical" style="position: relative; top: -74px; float: left;">
				<li class="rmItem rmFirst"><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Add Surgery</span></a></li><li class="rmItem "><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Admission Form</span></a></li><li class="rmItem "><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Allergy</span></a></li><li class="rmItem "><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Bed Transfer</span></a></li><li class="rmItem "><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Blood Requisition</span></a></li><li class="rmItem "><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Case Sheet</span></a></li><li class="rmItem "><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Death Summary</span></a></li><li class="rmItem "><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Diagnostic History</span></a></li><li class="rmItem "><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Discharge Summary</span></a></li><li class="rmItem "><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Drug Order</span></a></li><li class="rmItem "><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Non Drug Order</span></a></li><li class="rmItem "><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">OT Request</span></a></li><li class="rmItem "><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Patient Dashboard</span></a></li><li class="rmItem "><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Patient Vitals</span></a></li><li class="rmItem "><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Progress Notes</span></a></li><li class="rmItem "><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Provisional Diagnosis</span></a></li><li class="rmItem rmLast"><a href="#" class="rmLink" tabindex="0" style="width: 175px;"><span class="rmText">Referral History</span></a></li>
			</ul>
		<a href="#" tabindex="0" style="z-index: 2000; left: 0px; top: 0px;" class="rmTopArrow">&amp;nbsp;</a><a href="#" tabindex="0" style="z-index: 2000; left: 0px; bottom: 0px;" class="rmBottomArrowDisabled">&amp;nbsp;</a></div>
	</div>
