"""Authentication service interface."""

from typing import Protocol

from prisma.enums import UserRole
from prisma.models import User
from app.auth.schemas import AuthenticatedSession


class AuthenticationService(Protocol):

    async def authenticate(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str,
        last_name: str | None,
    ) -> AuthenticatedSession: ...

    async def login_to_emr(
        self,
        user: User,
        emr_username: str,
        emr_password: str,
    ) -> AuthenticatedSession: ...

    async def authorize(self, user: User, required_role: UserRole) -> None: ...

    async def approve(self, user_id: str) -> User: ...

    async def change_role(self, user_id: str, role: UserRole) -> User: ...