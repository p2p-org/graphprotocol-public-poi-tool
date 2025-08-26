class BisectorServiceError(Exception):
    """Base exception for bisector service."""


class ManifestNotFoundError(BisectorServiceError):
    """Raised when manifest cannot be retrieved for a deployment."""


class InvalidManifestError(BisectorServiceError):
    """Raised when manifest does not have start block."""


class SyncStatusNotFoundError(BisectorServiceError):
    """Raised when sync status cannot be retrieved for a deployment."""
