"""Authentication and authorization service."""

from __future__ import annotations

from prisma.enums import UserRole
from prisma.models import User

from app.database.repositories.user import UserRepository
from .exceptions import UserNotApproved, InsufficientPermissions

# Higher number = more privilege. ADMIN can do anything a DOCTOR/NURSE/
# READONLY can; NURSE cannot do anything requiring DOCTOR or ADMIN, etc.
_ROLE_RANK: dict[UserRole, int] = {
    UserRole.READONLY: 0,
    UserRole.NURSE: 1,
    UserRole.DOCTOR: 2,
    UserRole.ADMIN: 3,
}


class SessionAuthenticationService:
    """Authenticates Telegram users and authorizes role-gated actions."""

    def __init__(self, users: UserRepository) -> None:
        self.users = users

    async def authenticate(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str,
        last_name: str | None,
    ) -> User:
        """Look up or register a Telegram user; raise if not yet approved.

        If the user already exists, syncs username/first_name/last_name in
        case they changed their Telegram display info since last contact.
        """
        user = await self.users.get_by_telegram_id(telegram_id)

        if user is None:
            user = await self.users.register(
                telegram_id=telegram_id,
                first_name=first_name,
                username=username,
                last_name=last_name,
            )
        else:
            user = await self._sync_profile(user, username, first_name, last_name)

        if not user.approved:
            raise UserNotApproved(f"User {user.id} is not approved")

        return user

    async def _sync_profile(
        self,
        user: User,
        username: str | None,
        first_name: str,
        last_name: str | None,
    ) -> User:
        """Update stored profile fields that differ from the latest Telegram data."""
        changes: dict[str, str | None] = {}

        if username != user.username:
            changes["username"] = username
        if first_name != user.firstName:
            changes["first_name"] = first_name
        if last_name != user.lastName:
            changes["last_name"] = last_name

        if not changes:
            return user

        return await self.users.update_profile(user.id, **changes)

    async def authorize(self, user: User, required_role: UserRole) -> None:
        """Raise InsufficientPermissions if user's role is below required_role."""
        if _ROLE_RANK[user.role] < _ROLE_RANK[required_role]:
            raise InsufficientPermissions(
                f"User {user.id} has role {user.role}, requires at least {required_role}"
            )

    async def approve(self, user_id: str) -> User:
        """Approve a pending user."""
        return await self.users.approve(user_id)

    async def change_role(self, user_id: str, role: UserRole) -> User:
        """Change a user's role."""
        return await self.users.change_role(user_id, role)