import asyncio

from app.database.prisma import Database
from app.database.repositories.user import UserRepository
from app.database.repositories.session import SessionRepository
from app.database.exceptions import DatabaseError

TEST_TELEGRAM_ID = 987654321


async def main() -> None:
    db = Database()
    await db.connect()

    users = UserRepository(db)
    sessions = SessionRepository(db)

    try:
        # Clean slate
        existing = await users.get_by_telegram_id(TEST_TELEGRAM_ID)
        if existing is not None:
            await sessions.delete_user_sessions(existing.id)
            await users.delete(existing.id)
            print(f"Cleaned up leftover test user {existing.id}")

        # Set up a user to attach sessions to
        user = await users.register(
            telegram_id=TEST_TELEGRAM_ID,
            first_name="Test",
        )
        print("Test user created:", user.id)

        # 1. create_session
        storage_state = {"cookies": [{"name": "session", "value": "abc123"}]}
        session = await sessions.create_session(user.id, storage_state)
        print("Created session:", session)

        # 2. get_by_id
        fetched = await sessions.get_by_id(session.id)
        assert fetched is not None and fetched.id == session.id
        print("get_by_id OK")

        # 3. get_by_user
        user_sessions = await sessions.get_by_user(user.id)
        assert len(user_sessions) == 1
        print("get_by_user OK")

        # 4. get_active_session
        active = await sessions.get_active_session(user.id)
        assert active is not None and active.id == session.id
        print("get_active_session OK")

        # 5. save_storage_state
        new_state = {"cookies": [{"name": "session", "value": "updated456"}]}
        saved = await sessions.save_storage_state(session.id, new_state)
        assert saved.storageState == new_state
        print("save_storage_state OK")

        # 6. restore_storage_state
        restored = await sessions.restore_storage_state(session.id)
        assert restored == new_state
        print("restore_storage_state OK")

        # 7. update_last_login
        updated_login = await sessions.update_last_login(session.id)
        assert updated_login.lastLogin is not None
        print("update_last_login OK")

        # 8. update_expiry
        import datetime as dt
        future = dt.datetime.now(dt.UTC) + dt.timedelta(days=1)
        with_expiry = await sessions.update_expiry(session.id, future)
        assert with_expiry.expiresAt is not None
        print("update_expiry (set) OK")

        cleared = await sessions.update_expiry(session.id, None)
        assert cleared.expiresAt is None
        print("update_expiry (clear) OK")

        # 9. invalidate_session
        invalidated = await sessions.invalidate_session(session.id)
        assert invalidated.expiresAt is not None
        print("invalidate_session OK")

        # 10. delete_session
        deleted = await sessions.delete_session(session.id)
        print("Deleted session:", deleted.id)

        gone = await sessions.get_by_id(session.id)
        assert gone is None
        print("Confirmed session deletion")

        # 11. delete_user_sessions (create two more, then bulk-delete)
        await sessions.create_session(user.id, storage_state)
        await sessions.create_session(user.id, storage_state)
        count = await sessions.delete_user_sessions(user.id)
        assert count == 2
        print(f"delete_user_sessions deleted {count} session(s)")

        print("\nAll session checks passed.")

    except DatabaseError as e:
        print("DatabaseError during test run:", e)
        raise
    finally:
        # Final cleanup
        cleanup_user = await users.get_by_telegram_id(TEST_TELEGRAM_ID)
        if cleanup_user is not None:
            await sessions.delete_user_sessions(cleanup_user.id)
            await users.delete(cleanup_user.id)
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())