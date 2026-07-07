import asyncio

from app.database.prisma import Database
from app.database.repositories.user import UserRepository
from app.database.exceptions import DatabaseError
from prisma.enums import UserRole

TEST_TELEGRAM_ID = 123456789


async def main() -> None:
    db = Database()
    await db.connect()

    users = UserRepository(db)

    try:
        # Clean slate: remove any leftover test user from a previous run
        existing = await users.get_by_telegram_id(TEST_TELEGRAM_ID)
        if existing is not None:
            await users.delete(existing.id)
            print(f"Cleaned up leftover test user {existing.id}")

        # 1. register
        user = await users.register(
            telegram_id=TEST_TELEGRAM_ID,
            first_name="Emmanuel",
            last_name="Korir",
            username="emmanuel",
        )
        print("Registered:", user)

        # 2. exists
        assert await users.exists(TEST_TELEGRAM_ID) is True
        print("exists() OK")

        # 3. get_by_id / get_by_telegram_id
        by_id = await users.get_by_id(user.id)
        by_tg = await users.get_by_telegram_id(TEST_TELEGRAM_ID)
        assert by_id is not None and by_tg is not None
        assert by_id.id == by_tg.id == user.id
        print("get_by_id / get_by_telegram_id OK")

        # 4. update_profile
        updated = await users.update_profile(
            user.id,
            username="emmanuel_k",
            first_name="Emmanuel M.",
        )
        assert updated.username == "emmanuel_k"
        assert updated.firstName == "Emmanuel M."
        print("update_profile:", updated)

        # 5. change_role
        promoted = await users.change_role(user.id, UserRole.DOCTOR)
        assert promoted.role == UserRole.DOCTOR
        print("change_role:", promoted)

        # 6. approve / revoke
        approved = await users.approve(user.id)
        assert approved.approved is True
        print("approve:", approved)

        revoked = await users.revoke(user.id)
        assert revoked.approved is False
        print("revoke:", revoked)

        # 7. list_all contains our user
        all_users = await users.list_all()
        assert any(u.id == user.id for u in all_users)
        print(f"list_all: {len(all_users)} user(s) total")

        # 8. delete
        deleted = await users.delete(user.id)
        print("Deleted:", deleted)

        # 9. confirm gone
        gone = await users.get_by_id(user.id)
        assert gone is None
        print("Confirmed deletion")

        print("\nAll checks passed.")

    except DatabaseError as e:
        print("DatabaseError during test run:", e)
        raise
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())