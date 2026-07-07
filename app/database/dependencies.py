from app.database import Database


def get_database(database: Database) -> Database:
    """Return the configured database instance."""
    return database

# improve this once fastapi is configured
