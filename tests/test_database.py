from app.database.prisma import Database

async def main():
    db = Database()
    await db.connect()

    users = await db.client.user.find_many()
    print(users)

    await db.disconnect()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
    