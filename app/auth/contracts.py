"""Authentication service interface."""

from typing import Protocol

from prisma.enums import UserRole
from prisma.models import User


class AuthenticationService(Protocol):

    async def authenticate(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str,
        last_name: str | None,
    ) -> User: ...

    async def authorize(self, user: User, required_role: UserRole) -> None: ...

    async def approve(self, user_id: str) -> User: ...

    async def change_role(self, user_id: str, role: UserRole) -> User: ...