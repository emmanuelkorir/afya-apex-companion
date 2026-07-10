"""Runs patient searches against a user's already-live EMR page."""

from __future__ import annotations

from app.emr_client.exceptions import NoActiveEMRSession
from app.emr_client.live_page_registry import LivePageRegistry
from app.emr_client.pages.search_page import PatientSearchResult, SearchService


class SearchSessionManager:
    """Runs patient searches using the caller's existing live EMR page,
    and remembers the last search results per user so a follow-up
    selection can be resolved against them.
    """

    def __init__(
        self,
        registry: LivePageRegistry,
        search_service: SearchService,
    ) -> None:
        self.registry = registry
        self.search_service = search_service
        self._last_results: dict[str, list[PatientSearchResult]] = {}

    async def search(self, user_id: str, umr: str) -> tuple[list[PatientSearchResult], int]:
        """Run a UMR search for this user's live page.

        Returns (results, total_count) — results capped at 5 by SearchService.
        """
        page = self.registry.get_page(user_id)  # raises NoActiveEMRSession if none

        results = await self.search_service.search_by_umr(page, umr)
        total_count = await self.search_service.total_result_count(page)

        self._last_results[user_id] = results
        return results, total_count

    async def select(self, user_id: str, row_index: int) -> PatientSearchResult:
        """Select a result row from the user's last search and land on
        the patient dashboard.
        """
        results = self._last_results.get(user_id)
        if results is None:
            raise NoActiveEMRSession(f"No recent search results for user {user_id}")

        page = self.registry.get_page(user_id)
        result = results[row_index]
        await self.search_service.select_row(page, row_index)
        return result