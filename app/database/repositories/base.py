"""Base repository."""

from app.database.prisma import Database


class BaseRepository:
    """Base repository."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.client = database.client