"""Database connection."""

from prisma import Prisma


class Database:
    """Database wrapper around Prisma."""

    def __init__(self) -> None:
        self.client = Prisma()

    async def connect(self) -> None:
        await self.client.connect()

    async def disconnect(self) -> None:
        await self.client.disconnect()