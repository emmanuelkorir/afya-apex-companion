"""Authentication and authorization service."""

from __future__ import annotations
from datetime import UTC, datetime

from prisma.enums import UserRole
from prisma.models import User
from app.database.repositories.user import UserRepository
from app.auth.schemas import AuthenticatedSession
from app.emr_client.session_manager import EMRSessionManager
from .exceptions import UserNotApproved, InsufficientPermissions

_ROLE_RANK: dict[UserRole, int] = {
    UserRole.READONLY: 0,
    UserRole.NURSE: 1,
    UserRole.DOCTOR: 2,
    UserRole.ADMIN: 3,
}


class SessionAuthenticationService:
    """Authenticates Telegram users and orchestrates their EMR session state.

    Deliberately has no knowledge of Playwright, browser contexts, or
    SessionRepository — all of that lives behind EMRSessionManager.
    """

    def __init__(
        self,
        users: UserRepository,
        emr: EMRSessionManager,
    ) -> None:
        self.users = users
        self.emr = emr

    async def authenticate(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str,
        last_name: str | None,
    ) -> AuthenticatedSession:
        """Look up or register a Telegram user; raise if not yet approved.

        Does NOT perform EMR login. Returns an AuthenticatedSession whose
        `requires_login` flag tells the caller whether to prompt for EMR
        credentials.
        """
        existing_user = await self.users.get_by_telegram_id(telegram_id)

        if existing_user is None:
            existing_user = await self.users.register(
                telegram_id=telegram_id,
                first_name=first_name,
                username=username,
                last_name=last_name,
            )
        else:
            existing_user = await self._sync_profile(
                existing_user, username, first_name, last_name
            )

        if not existing_user.approved:
            raise UserNotApproved(f"User {existing_user.id} is not approved")

        return await self._build_session(existing_user)
    
    async def login_to_emr(
        self,
        user: User,
        emr_username: str,
        emr_password: str,
    ) -> AuthenticatedSession:
        """Perform a fresh EMR login and return the updated AuthenticatedSession."""
        await self.emr.login(user.id, emr_username, emr_password)

        if user.emrUsername != emr_username:
            user = await self.users.set_emr_username(user.id, emr_username)

        return await self._build_session(user)

    async def _build_session(self, user: User) -> AuthenticatedSession:
        requires_login = not self.emr.is_logged_in(user.id)
        return AuthenticatedSession(
            user=user,
            emr_session=None,  # no longer meaningful — live session, not a DB row
            authenticated_at=datetime.now(UTC),
            requires_login=requires_login,
        )

    async def _sync_profile(
        self,
        user: User,
        username: str | None,
        first_name: str,
        last_name: str | None,
    ) -> User:
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
        if _ROLE_RANK[user.role] < _ROLE_RANK[required_role]:
            raise InsufficientPermissions(
                f"User {user.id} has role {user.role}, requires at least {required_role}"
            )

    async def approve(self, user_id: str) -> User:
        return await self.users.approve(user_id)

    async def change_role(self, user_id: str, role: UserRole) -> User:
        return await self.users.change_role(user_id, role)