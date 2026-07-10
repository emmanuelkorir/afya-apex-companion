class EMRLoginError(Exception):
    """Raised when Playwright fails to authenticate against the EMR."""


class NoActiveEMRSession(Exception):
    """Raised when a user tries to search without a valid, unexpired EMR session."""


class EMRSessionRejected(Exception):
    """Raised when a stored session looked valid but the EMR rejected it
    (redirected to Login.aspx). Means our TTL assumption is wrong, or the
    EMR invalidates sessions for reasons cookies alone don't capture.
    """

class ProgressNoteConversationActive(Exception):
    """Raised when a user tries to start a new /ward search or a new
    progress-note flow while one is already in progress for them.

    Branch 7: reject with a message to /cancel first, rather than silently
    cancelling the in-flight conversation - two flows racing on the same
    Playwright Page would corrupt EMR page state.
    """