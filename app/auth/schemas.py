"""Auth-related runtime DTOs."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

from prisma.models import User, EMRSession


@dataclass(slots=True)
class AuthenticatedSession:
    """Runtime object representing an authenticated Telegram user and their EMR context.

    Not persisted — constructed fresh on each authentication.
    """

    user: User
    emr_session: EMRSession | None
    authenticated_at: datetime
    requires_login: bool