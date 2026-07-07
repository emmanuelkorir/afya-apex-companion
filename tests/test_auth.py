import asyncio

from app.database.prisma import Database
from app.database.repositories.user import UserRepository
from app.auth import SessionAuthenticationService, UserNotApproved, InsufficientPermissions
from prisma.enums import UserRole

TEST_TELEGRAM_ID = 555111222


async def main() -> None:
    db = Database()
    await db.connect()

    users = UserRepository(db)
    auth = SessionAuthenticationService(users)

    try:
        existing = await users.get_by_telegram_id(TEST_TELEGRAM_ID)
        if existing is not None:
            await users.delete(existing.id)
            print("Cleaned up leftover test user")

        # 1. First authenticate call auto-registers, but user isn't approved yet
        try:
            await auth.authenticate(
                telegram_id=TEST_TELEGRAM_ID,
                username="testnurse",
                first_name="Test",
                last_name="Nurse",
            )
            raise AssertionError("Expected UserNotApproved")
        except UserNotApproved:
            print("UserNotApproved raised correctly for unapproved user")

        # 2. Approve them
        user = await users.get_by_telegram_id(TEST_TELEGRAM_ID)
        assert user is not None
        await auth.approve(user.id)
        print("User approved")

        # 3. Now authenticate should succeed
        authed = await auth.authenticate(
            telegram_id=TEST_TELEGRAM_ID,
            username="testnurse",
            first_name="Test",
            last_name="Nurse",
        )
        assert authed.approved is True
        print("authenticate() succeeded post-approval:", authed.id)

        # 4. Default role is READONLY — should fail a DOCTOR-gated check
        try:
            await auth.authorize(authed, UserRole.DOCTOR)
            raise AssertionError("Expected InsufficientPermissions")
        except InsufficientPermissions:
            print("InsufficientPermissions raised correctly for READONLY vs DOCTOR")

        # 5. Promote to NURSE — still shouldn't pass a DOCTOR check
        await auth.change_role(authed.id, UserRole.NURSE)
        nurse = await users.get_by_id(authed.id)
        assert nurse is not None
        try:
            await auth.authorize(nurse, UserRole.DOCTOR)
            raise AssertionError("Expected InsufficientPermissions")
        except InsufficientPermissions:
            print("NURSE correctly blocked from DOCTOR-gated action")

        # 6. Promote to ADMIN — should pass a DOCTOR check (hierarchy)
        await auth.change_role(authed.id, UserRole.ADMIN)
        admin = await users.get_by_id(authed.id)
        assert admin is not None
        await auth.authorize(admin, UserRole.DOCTOR)
        print("ADMIN correctly passes DOCTOR-gated action (hierarchy works)")

        # 7. Exact-match case: DOCTOR should pass a NURSE-gated check too
        await auth.change_role(authed.id, UserRole.DOCTOR)
        doctor = await users.get_by_id(authed.id)
        assert doctor is not None
        await auth.authorize(doctor, UserRole.NURSE)
        print("DOCTOR correctly passes NURSE-gated action")

                # 8. Re-authenticate with a changed username — should sync
        resynced = await auth.authenticate(
            telegram_id=TEST_TELEGRAM_ID,
            username="testnurse_renamed",
            first_name="Test",
            last_name="Nurse",
        )
        assert resynced.username == "testnurse_renamed"
        print("Profile sync on re-authenticate works")

        print("\nAll auth checks passed.")

    finally:
        cleanup = await users.get_by_telegram_id(TEST_TELEGRAM_ID)
        if cleanup is not None:
            await users.delete(cleanup.id)
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())