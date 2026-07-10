"""Playwright page management for the Ward Management page."""

from __future__ import annotations

from dataclasses import dataclass

from playwright.async_api import Locator, Page, expect

from app.emr_client.onclick_parser import extract_umr_and_visit_no


@dataclass(slots=True)
class PatientWardInfo:
    """Dataclass holding patient information from the Ward Management page."""
    row_index: int
    patient_name: str
    age: str
    admission_time: str
    ward_name: str
    length_of_stay: str
    # Branch 11: the ward grid has no dedicated <span id="...lblUMR"> the
    # way the UMR-search grid does - these come from parsing the row's
    # showMenu(...) onclick attribute instead. Shown to the doctor before
    # they pick a row, so a same-name mixup is caught before any note gets
    # written to the wrong chart.
    umr: str = ""
    visit_no: str = ""


async def wait_for_telerik(page: Page) -> None:
    """Wait for ASP.NET AJAX/Telerik to finish processing."""
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_function(
        """
        () => {
            if (!window.Sys) return true;
            return !Sys.WebForms.PageRequestManager
                .getInstance()
                .get_isInAsyncPostBack();
        }
        """
    )


class WardManagementService:
    """
    Stateless service for Ward Management page interactions.

    All methods accept a Playwright Page instance so that the caller
    (e.g., WardSessionManager) supplies the correct page for each user.
    """

    async def search_by_umr(self, page: Page, umr: str) -> None:
        """
        Navigate to Ward Management, select UMR filter, and search.

        Args:
            page: The Playwright Page object.
            umr: The UMR to search for.

        Raises:
            Exception: If navigation or filtering fails.
        """
        # 1. Wait for a post-login element
        await expect(
            page.locator("#RAD_SLIDING_PANE_TEXT_ctl00_rsp1")
        ).to_be_visible(timeout=30000)

        # 2. Navigate to Ward Management
        await page.locator("#RAD_SLIDING_PANE_TEXT_ctl00_rsp1").click()
        await page.get_by_role("link", name="Ward Management").click()
        await wait_for_telerik(page)

        # 3. Open dropdown and select "UMR"
        arrow = page.locator("#ctl00_ContentPlaceHolder1_ddlName_Arrow")
        await expect(arrow).to_be_visible(timeout=10000)
        await expect(arrow).to_be_enabled()
        await arrow.scroll_into_view_if_needed()

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

        # 4. Enter UMR and filter
        await page.locator("#ctl00_ContentPlaceHolder1_txtSearchContent").fill(umr)
        await page.get_by_role("button", name="Filter").click()

        # 5. Wait for results table
        table_selector = "#ctl00_ContentPlaceHolder1_gvWardDtl"
        try:
            await page.wait_for_selector(table_selector, state="visible", timeout=15000)
        except Exception as e:
            raise RuntimeError("Table did not appear after filtering.") from e

        await wait_for_telerik(page)

    async def extract_all_patients(self, page: Page) -> list[PatientWardInfo]:
        """
        Extract all patient rows from the currently visible table.

        Args:
            page: The Playwright Page object.

        Returns:
            List of PatientWardInfo objects (empty if no rows).

        Raises:
            RuntimeError: If the table is not visible.
        """
        table_selector = "#ctl00_ContentPlaceHolder1_gvWardDtl"
        if not await page.locator(table_selector).is_visible():
            raise RuntimeError("Ward Management table is not visible.")

        rows = page.locator(
            f"{table_selector} tbody tr.rgRow, {table_selector} tbody tr.rgAltRow"
        )
        count = await rows.count()
        if count == 0:
            return []

        patients = []
        for idx in range(count):
            row = rows.nth(idx)
            patient = await self._extract_patient_from_row(row, idx)
            patients.append(patient)
        return patients

    async def _extract_patient_from_row(self, row: Locator, row_index: int) -> PatientWardInfo:
        """Extract data from a single row."""
        name_span = row.locator("span[id*='_lblPatientName']")
        patient_name = (await name_span.text_content()) or ""

        age_span = row.locator("span[id*='_lblAgeGender']")
        age = (await age_span.text_content()) or ""

        # Find admission time: a td with a date pattern
        admission_time = ""
        all_tds = row.locator("td")
        td_count = await all_tds.count()
        for i in range(td_count):
            td = all_tds.nth(i)
            text = (await td.text_content()) or ""
            if "/" in text and len(text.strip()) >= 10 and "Dr." not in text:
                admission_time = text.strip()
                break

        ward_hidden = row.locator("input[id*='hdnBedCategoryNameForDisplay']")
        ward_name = (await ward_hidden.get_attribute("value")) or ""

        los_span = row.locator("span[id*='_lblLOS']")
        length_of_stay = (await los_span.text_content()) or ""

        # Branch 11: UMR/visit_no live only in the first <td>'s
        # showMenu(...) onclick attribute - no dedicated span for them.
        # Non-strict: a single malformed onclick shouldn't fail the whole
        # /ward search, it just surfaces as an empty UMR the UI can flag.
        first_td = all_tds.first
        onclick = (await first_td.get_attribute("onclick")) or ""
        umr, visit_no = extract_umr_and_visit_no(onclick, strict=False)

        return PatientWardInfo(
            row_index=row_index,
            patient_name=patient_name.strip(),
            age=age.strip(),
            admission_time=admission_time.strip(),
            ward_name=ward_name.strip(),
            length_of_stay=length_of_stay.strip(),
            umr=umr,
            visit_no=visit_no,
        )

    async def select_row(self, page: Page, row_index: int) -> None:
        """
        Click on a specific row to open the patient's detail page.

        The first cell of each row has an `onclick` attribute that opens
        a context menu (showMenu(...) -> Telerik RadMenu). We click the
        row's first <td>.

        Args:
            page: The Playwright Page object.
            row_index: Zero-based index of the row to select.

        Raises:
            IndexError: If the row does not exist.
        """
        table_selector = "#ctl00_ContentPlaceHolder1_gvWardDtl"
        rows = page.locator(
            f"{table_selector} tbody tr.rgRow, {table_selector} tbody tr.rgAltRow"
        )
        if await rows.count() <= row_index:
            raise IndexError(f"Row index {row_index} out of range.")
        row = rows.nth(row_index)
        # Click the first cell (which contains the patient name and opens
        # the showMenu(...) context menu).
        await row.locator("td").first.click()
        # Wait for navigation (if any) or a new page element
        await page.wait_for_load_state("networkidle")
        # Optionally wait for Telerik postback if applicable
        await wait_for_telerik(page)