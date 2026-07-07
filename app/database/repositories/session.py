"""Repository for EMR browser sessions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from prisma import Json
from prisma.models import EMRSession
from prisma.types import EMRSessionCreateInput, EMRSessionUpdateInput
from prisma.errors import PrismaError
from app.database.exceptions import DatabaseError
from .base import BaseRepository


class SessionRepository(BaseRepository):
    """Repository for managing EMR browser sessions."""

    async def create_session(
        self,
        user_id: str,
        storage_state: dict,
        expires_at: datetime | None = None,
    ) -> EMRSession:
        """Create a new browser session for a user."""
        try:
            data: EMRSessionCreateInput = {
                "user": {"connect": {"id": user_id}},
                "storageState": Json(storage_state),
                "lastLogin": datetime.now(UTC),
            }
            if expires_at is not None:
                data["expiresAt"] = expires_at

            return await self.client.emrsession.create(data=data)
        except PrismaError as e:
            raise DatabaseError(f"Failed to create session for user {user_id}") from e
        except Exception as e:
            raise DatabaseError(f"Unexpected error creating session for user {user_id}") from e

    async def get_by_id(self, session_id: str) -> EMRSession | None:
        """Retrieve a session by its ID."""
        try:
            return await self.client.emrsession.find_unique(
                where={"id": session_id}
            )
        except PrismaError as e:
            raise DatabaseError(f"Failed to fetch session by id {session_id}") from e
        except Exception as e:
            raise DatabaseError(f"Unexpected error fetching session {session_id}") from e

    async def get_by_user(self, user_id: str) -> list[EMRSession]:
        """Retrieve all sessions belonging to a user."""
        try:
            return await self.client.emrsession.find_many(
                where={"userId": user_id}
            )
        except PrismaError as e:
            raise DatabaseError(f"Failed to fetch sessions for user {user_id}") from e
        except Exception as e:
            raise DatabaseError(f"Unexpected error fetching sessions for user {user_id}") from e

    async def get_active_session(self, user_id: str) -> EMRSession | None:
        """Return the most recently updated session for a user."""
        try:
            sessions = await self.client.emrsession.find_many(
                where={"userId": user_id},
                order={"updatedAt": "desc"},
                take=1,
            )
            return sessions[0] if sessions else None
        except PrismaError as e:
            raise DatabaseError(f"Failed to fetch active session for user {user_id}") from e
        except Exception as e:
            raise DatabaseError(f"Unexpected error fetching active session for user {user_id}") from e

    async def save_storage_state(
        self,
        session_id: str,
        storage_state: dict,
    ) -> EMRSession:
        """Persist the latest Playwright storage state."""
        try:
            data: EMRSessionUpdateInput = {"storageState": Json(storage_state)}
            result = await self.client.emrsession.update(
                where={"id": session_id},
                data=data,
            )
            if result is None:
                raise DatabaseError(f"Session {session_id} not found")
            return result
        except PrismaError as e:
            raise DatabaseError(f"Failed to save storage state for session {session_id}") from e
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Unexpected error saving storage state for session {session_id}") from e

    async def restore_storage_state(self, session_id: str) -> dict | None:
        """Retrieve a stored Playwright storage state."""
        try:
            session = await self.get_by_id(session_id)
            if session is None:
                return None
            # storageState is a Prisma Json field, typed loosely at the ORM level.
            return cast("dict | None", session.storageState)
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Unexpected error restoring storage state for session {session_id}") from e

    async def update_last_login(self, session_id: str) -> EMRSession:
        """Update the last successful login timestamp."""
        try:
            data: EMRSessionUpdateInput = {"lastLogin": datetime.now(UTC)}
            result = await self.client.emrsession.update(
                where={"id": session_id},
                data=data,
            )
            if result is None:
                raise DatabaseError(f"Session {session_id} not found")
            return result
        except PrismaError as e:
            raise DatabaseError(f"Failed to update last login for session {session_id}") from e
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Unexpected error updating last login for session {session_id}") from e

    async def update_expiry(
        self,
        session_id: str,
        expires_at: datetime | None,
    ) -> EMRSession:
        """Update the session expiry time (pass None to clear it)."""
        try:
            data: EMRSessionUpdateInput = {"expiresAt": expires_at}
            result = await self.client.emrsession.update(
                where={"id": session_id},
                data=data,
            )
            if result is None:
                raise DatabaseError(f"Session {session_id} not found")
            return result
        except PrismaError as e:
            raise DatabaseError(f"Failed to update expiry for session {session_id}") from e
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Unexpected error updating expiry for session {session_id}") from e

    async def invalidate_session(self, session_id: str) -> EMRSession:
        """Invalidate a browser session by setting expiry to now."""
        try:
            data: EMRSessionUpdateInput = {"expiresAt": datetime.now(UTC)}
            result = await self.client.emrsession.update(
                where={"id": session_id},
                data=data,
            )
            if result is None:
                raise DatabaseError(f"Session {session_id} not found")
            return result
        except PrismaError as e:
            raise DatabaseError(f"Failed to invalidate session {session_id}") from e
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Unexpected error invalidating session {session_id}") from e

    async def delete_session(self, session_id: str) -> EMRSession:
        """Delete a session."""
        try:
            result = await self.client.emrsession.delete(where={"id": session_id})
            if result is None:
                raise DatabaseError(f"Session {session_id} not found")
            return result
        except PrismaError as e:
            raise DatabaseError(f"Failed to delete session {session_id}") from e
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Unexpected error deleting session {session_id}") from e

    async def delete_user_sessions(self, user_id: str) -> int:
        """Delete all sessions belonging to a user."""
        try:
            return await self.client.emrsession.delete_many(
                where={"userId": user_id}
            )
        except PrismaError as e:
            raise DatabaseError(f"Failed to delete sessions for user {user_id}") from e
        except Exception as e:
            raise DatabaseError(f"Unexpected error deleting sessions for user {user_id}") from e