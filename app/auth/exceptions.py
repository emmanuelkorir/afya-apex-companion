"""Authentication and authorization exceptions."""


class AuthenticationError(Exception):
    """Base authentication exception."""


class UserNotApproved(AuthenticationError):
    """User has registered but is not yet approved."""


class InsufficientPermissions(AuthenticationError):
    """User's role does not permit this action."""