"""Database exceptions."""


class DatabaseError(Exception):
    """Base database exception."""


class EntityNotFound(DatabaseError):
    """Entity was not found."""


class DuplicateEntity(DatabaseError):
    """Duplicate entity exists."""

