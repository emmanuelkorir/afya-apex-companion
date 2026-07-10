"""Manages ward patient searches and selections for users with active EMR pages."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.emr_client.browser_helpers import click_menu_item
from app.emr_client.exceptions import (
    NoActiveEMRSession,
    ProgressNoteConversationActive,
)
from app.emr_client.live_page_registry import LivePageRegistry
from app.emr_client.pages.progress_notes_page import (
    FailureDiagnostics,
    ProgressNotesService,
    SaveResult,
)
from app.emr_client.pages.wardmanagement_page import (
    PatientWardInfo,
    WardManagementService,
)

_PROGRESS_NOTES_MENU_TEXT = "Progress Notes"
_DWR_PREFIX_FORMAT = "DWR %d/%m/%Y %H:%M"


class WardSessionManager:
    """
    Manages ward patient operations using a user's existing live EMR page.

    Delegates to stateless WardManagementService / ProgressNotesService for
    page interactions, and remembers per-user: the last search results, and
    whether a progress-note flow is currently in progress (branch 7:
    prevents a second /ward search or menu action from racing on the same
    Playwright Page while one is active).
    """

    def __init__(
        self,
        registry: LivePageRegistry,
        ward_service: WardManagementService,
        progress_notes_service: Optional[ProgressNotesService] = None,
    ) -> None:
        self.registry = registry
        self.ward_service = ward_service
        self.progress_notes_service = progress_notes_service or ProgressNotesService()
        self._last_results: dict[str, list[PatientWardInfo]] = {}
        self._active_progress_note: set[str] = set()

    # ------------------------------------------------------------------
    # Search / selection (existing behavior, now concurrency-guarded)
    # ------------------------------------------------------------------

    async def search_by_umr(self, user_id: str, umr: str) -> list[PatientWardInfo]:
        """
        Search for a patient by UMR on the Ward Management page.

        Raises:
            NoActiveEMRSession: If the user has no active EMR page.
            ProgressNoteConversationActive: If a progress-note flow is
                already in progress for this user (branch 7) - they must
                finish or /cancel it first.
        """
        self._raise_if_progress_note_active(user_id)

        page = self.registry.get_page(user_id)  # may raise NoActiveEMRSession

        await self.ward_service.search_by_umr(page, umr)
        results = await self.ward_service.extract_all_patients(page)

        self._last_results[user_id] = results
        return results

    async def select_patient(self, user_id: str, row_index: int) -> None:
        """
        Select a patient row from the last search results to open their
        details (dashboard navigation - unrelated to the action-menu flow
        below, kept for backward compatibility with existing callers).
        """
        results = self._get_last_results_or_raise(user_id)
        self._validate_row_index(row_index, results)

        page = self.registry.get_page(user_id)
        await self.ward_service.select_row(page, row_index)

    def get_last_results(self, user_id: str) -> Optional[list[PatientWardInfo]]:
        """Return the last cached search results for a user, or None."""
        return self._last_results.get(user_id)

    # ------------------------------------------------------------------
    # Progress Notes flow (branches 1, 5, 7, 11-13)
    # ------------------------------------------------------------------

    async def open_progress_notes_for_patient(self, user_id: str, row_index: int) -> None:
        """
        Open the patient's context menu, click "Progress Notes", and wait
        for the popup to be ready.

        Marks the user as having an active progress-note conversation,
        blocking new /ward searches until cancel_progress_note() or a
        successful save + close_progress_note().

        Raises:
            NoActiveEMRSession: If the user has no active EMR page.
            IndexError: If row_index doesn't match the last search results.
        """
        results = self._get_last_results_or_raise(user_id)
        self._validate_row_index(row_index, results)

        page = self.registry.get_page(user_id)

        await self.ward_service.select_row(page, row_index)
        await click_menu_item(page, _PROGRESS_NOTES_MENU_TEXT)
        await self.progress_notes_service.open(page)

        self._active_progress_note.add(user_id)

    def has_active_progress_note(self, user_id: str) -> bool:
        return user_id in self._active_progress_note

    async def fill_progress_note(self, user_id: str, note_text: str) -> None:
        """
        Fill the note editor with note_text, auto-prefixed with a
        "DWR {date} {time}:" timestamp (branch 4).
        """
        page = self.registry.get_page(user_id)
        prefixed = f"{datetime.now().strftime(_DWR_PREFIX_FORMAT)}: {note_text}"
        await self.progress_notes_service.fill_note(page, prefixed)

    async def save_progress_note(self, user_id: str) -> SaveResult:
        """
        Attempt to save the note. Does not clear the active-conversation
        flag on failure (branch 5) - the caller presents retry-or-cancel
        and the user is still "in" the flow either way.
        """
        page = self.registry.get_page(user_id)
        return await self.progress_notes_service.save(page)

    async def capture_progress_note_failure_diagnostics(
        self, user_id: str
    ) -> FailureDiagnostics:
        """Screenshot + popup HTML for an unconfirmed save (branch 5)."""
        page = self.registry.get_page(user_id)
        return await self.progress_notes_service.capture_failure_diagnostics(page)

    async def close_progress_note(self, user_id: str) -> None:
        """
        Close the popup after a successful save. Clears the active-
        conversation flag, re-enabling /ward searches for this user.
        """
        page = self.registry.get_page(user_id)
        await self.progress_notes_service.close(page)
        self._active_progress_note.discard(user_id)

    async def cancel_progress_note(self, user_id: str) -> None:
        """
        Close the popup without requiring a successful save (user chose
        "cancel" after a save failure, or aborted via /cancel). Clears the
        active-conversation flag.
        """
        page = self.registry.get_page(user_id)
        await self.progress_notes_service.close(page)
        self._active_progress_note.discard(user_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _raise_if_progress_note_active(self, user_id: str) -> None:
        if user_id in self._active_progress_note:
            raise ProgressNoteConversationActive(
                f"User {user_id} has an in-progress progress note. "
                "Finish it or send /cancel first."
            )

    def _get_last_results_or_raise(self, user_id: str) -> list[PatientWardInfo]:
        results = self._last_results.get(user_id)
        if results is None:
            raise NoActiveEMRSession(
                f"No recent ward search results for user {user_id}. "
                "Please run a search first."
            )
        return results

    @staticmethod
    def _validate_row_index(row_index: int, results: list[PatientWardInfo]) -> None:
        if row_index < 0 or row_index >= len(results):
            raise IndexError(
                f"Row index {row_index} out of range. "
                f"Available rows: 0-{len(results) - 1}."
            )