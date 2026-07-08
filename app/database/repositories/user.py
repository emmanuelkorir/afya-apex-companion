"""Repository for User persistence."""

from __future__ import annotations

from prisma.models import User
from prisma.types import UserCreateInput, UserUpdateInput
from prisma.enums import UserRole
from prisma.errors import PrismaError

from app.database.exceptions import DatabaseError
from .base import BaseRepository


class UserRepository(BaseRepository):
    """Repository for managing application users."""

    async def register(
        self,
        telegram_id: int,
        first_name: str,
        username: str | None = None,
        last_name: str | None = None,
    ) -> User:
        """Register a new Telegram user."""
        try:
            data: UserCreateInput = {
                "telegramId": telegram_id,
                "firstName": first_name,
            }
            if username is not None:
                data["username"] = username
            if last_name is not None:
                data["lastName"] = last_name

            return await self.client.user.create(data=data)
        except PrismaError as e:
            raise DatabaseError(f"Failed to register user with telegram_id {telegram_id}") from e
        except Exception as e:
            raise DatabaseError(f"Unexpected error during registration of telegram_id {telegram_id}") from e

    async def get_by_id(self, user_id: str) -> User | None:
        """Retrieve a user by ID."""
        try:
            return await self.client.user.find_unique(where={"id": user_id})
        except PrismaError as e:
            raise DatabaseError(f"Failed to fetch user by id {user_id}") from e
        except Exception as e:
            raise DatabaseError(f"Unexpected error fetching user by id {user_id}") from e

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Retrieve a user by Telegram ID."""
        try:
            return await self.client.user.find_unique(where={"telegramId": telegram_id})
        except PrismaError as e:
            raise DatabaseError(f"Failed to fetch user by telegram_id {telegram_id}") from e
        except Exception as e:
            raise DatabaseError(f"Unexpected error fetching user by telegram_id {telegram_id}") from e

    async def update_profile(
        self,
        user_id: str,
        *,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> User:
        """Update a user's profile.

        Only fields explicitly passed (non-None) are updated. Because
        `firstName` is non-nullable in the schema, there is no way to
        "clear" it — pass a real value or omit it. `lastName` is nullable,
        but this method only ever sets it, never clears it back to null;
        add an explicit sentinel if you need that behavior later.
        """
        try:
            data: UserUpdateInput = {}
            if username is not None:
                data["username"] = username
            if first_name is not None:
                data["firstName"] = first_name
            if last_name is not None:
                data["lastName"] = last_name

            result = await self.client.user.update(
                where={"id": user_id},
                data=data,
            )
            if result is None:
                raise DatabaseError(f"User {user_id} not found")
            return result
        except PrismaError as e:
            raise DatabaseError(f"Failed to update profile for user {user_id}") from e
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Unexpected error updating profile for user {user_id}") from e

    async def change_role(self, user_id: str, role: UserRole) -> User:
        """Change a user's role."""
        try:
            data: UserUpdateInput = {"role": role}
            result = await self.client.user.update(
                where={"id": user_id},
                data=data,
            )
            if result is None:
                raise DatabaseError(f"User {user_id} not found")
            return result
        except PrismaError as e:
            raise DatabaseError(f"Failed to change role for user {user_id}") from e
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Unexpected error changing role for user {user_id}") from e

    async def approve(self, user_id: str) -> User:
        """Approve a user."""
        try:
            data: UserUpdateInput = {"approved": True}
            result = await self.client.user.update(
                where={"id": user_id},
                data=data,
            )
            if result is None:
                raise DatabaseError(f"User {user_id} not found")
            return result
        except PrismaError as e:
            raise DatabaseError(f"Failed to approve user {user_id}") from e
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Unexpected error approving user {user_id}") from e

    async def revoke(self, user_id: str) -> User:
        """Revoke a user's approval."""
        try:
            data: UserUpdateInput = {"approved": False}
            result = await self.client.user.update(
                where={"id": user_id},
                data=data,
            )
            if result is None:
                raise DatabaseError(f"User {user_id} not found")
            return result
        except PrismaError as e:
            raise DatabaseError(f"Failed to revoke user {user_id}") from e
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Unexpected error revoking user {user_id}") from e

    async def exists(self, telegram_id: int) -> bool:
        """Check whether a Telegram user exists."""
        try:
            user = await self.get_by_telegram_id(telegram_id)
            return user is not None
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to check existence of user with telegram_id {telegram_id}") from e

    async def list_all(self) -> list[User]:
        """Return all users ordered by creation date."""
        try:
            return await self.client.user.find_many(
                order={"createdAt": "desc"}
            )
        except PrismaError as e:
            raise DatabaseError("Failed to fetch all users") from e
        except Exception as e:
            raise DatabaseError("Unexpected error fetching all users") from e

    async def delete(self, user_id: str) -> User:
        """Delete a user."""
        try:
            result = await self.client.user.delete(where={"id": user_id})
            if result is None:
                raise DatabaseError(f"User {user_id} not found")
            return result
        except PrismaError as e:
            raise DatabaseError(f"Failed to delete user {user_id}") from e
        except DatabaseError:
            raise
        except Exception as e:
            raise DatabaseError(f"Unexpected error deleting user {user_id}") from e
        
    async def set_emr_username(self, user_id: str, emr_username: str) -> User:
        """Store the user's EMR username after their first successful EMR login."""
        try:
            result = await self.client.user.update(
                where={"id": user_id},
                data={"emrUsername": emr_username},
            )
            if result is None:
                raise DatabaseError(f"User {user_id} not found")
            return result
        except PrismaError as e:
            raise DatabaseError(f"Failed to set EMR username for user {user_id}") from e
        except Exception as e:
            raise DatabaseError(f"Unexpected error setting EMR username for user {user_id}") from e