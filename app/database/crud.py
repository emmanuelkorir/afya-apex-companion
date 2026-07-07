from typing import Any, cast
from prisma import Json
from app.database.db import db

StorageState = dict[str, Any]


async def save_session(telegram_user_id: str, storage_state: StorageState):
    """
    Saves or updates the Playwright browser state.
    """
    await db.emrsession.upsert(
        where={
            "telegram_user_id": telegram_user_id
        },
        data={
            "create": {
                "telegram_user_id": telegram_user_id,
                "storage_state": Json(storage_state),
            },
            "update": {
                "storage_state": Json(storage_state),
            }
        }
    )


async def get_session(telegram_user_id: str) -> StorageState | None:
    """
    Retrieves the Playwright browser state if it exists.
    """
    session = await db.emrsession.find_unique(
        where={
            "telegram_user_id": telegram_user_id
        }
    )

    if session is None:
        return None

    return cast(StorageState, session.storage_state)


async def delete_session(telegram_user_id: str):
    """
    Deletes the session (used when cookies expire).
    """
    try:
        await db.emrsession.delete(
            where={
                "telegram_user_id": telegram_user_id
            }
        )
    except Exception:
        pass