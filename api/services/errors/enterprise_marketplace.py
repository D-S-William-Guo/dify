"""Enterprise marketplace service domain errors.

Every error carries a stable ``code``, ``status_code``, and a client-safe
``message``.  The message MUST NOT contain DSL content, email, tokens,
credentials, connection strings, SQL, or internal exception text.
"""


class MarketplaceError(Exception):
    """Base exception for marketplace service errors."""

    code: str = "marketplace_error"
    status_code: int = 400
    message: str = "Marketplace error"

    def __init__(self, description: str | None = None):
        self.description = description or self.message
        super().__init__(self.description)


class SourceAppNotFound(MarketplaceError):
    code = "source_app_not_found"
    status_code = 404
    message = "Source app not found"


class AssetNotFound(MarketplaceError):
    code = "asset_not_found"
    status_code = 404
    message = "Marketplace asset not found"


class SubmissionAlreadyPending(MarketplaceError):
    code = "submission_already_pending"
    status_code = 409
    message = "A pending submission already exists for this app"


class InvalidStatusTransition(MarketplaceError):
    code = "invalid_status_transition"
    status_code = 409
    message = "Invalid status transition"


class AssetAlreadyUnlisted(MarketplaceError):
    code = "asset_already_unlisted"
    status_code = 409
    message = "Asset is already unlisted"


class StaleAssetVersion(MarketplaceError):
    code = "stale_asset_version"
    status_code = 409
    message = "Asset has been modified; please refresh and retry"


class ConcurrentOperation(MarketplaceError):
    code = "concurrent_operation"
    status_code = 409
    message = "Concurrent operation detected; retry"


class SourceAppUnavailable(MarketplaceError):
    code = "source_app_unavailable"
    status_code = 409
    message = "Source app is unavailable"


class SnapshotNotReady(MarketplaceError):
    code = "snapshot_not_ready"
    status_code = 409
    message = "Snapshot is not ready"


class SnapshotIntegrityError(MarketplaceError):
    code = "snapshot_integrity_error"
    status_code = 409
    message = "Snapshot integrity check failed"


class SnapshotContainsSecret(MarketplaceError):
    code = "snapshot_contains_secret"
    status_code = 422
    message = "Snapshot contains secret or credential data"


class NonportableResourceReference(MarketplaceError):
    code = "nonportable_resource_reference"
    status_code = 422
    message = "Non-portable resource reference detected"


class PrivatePluginDependency(MarketplaceError):
    code = "private_plugin_dependency"
    status_code = 422
    message = "Private plugin dependency cannot be shared"


class DependencyUnavailable(MarketplaceError):
    code = "dependency_unavailable"
    status_code = 409
    message = "Required plugin dependency is unavailable in target workspace"


class DependencyServiceUnavailable(MarketplaceError):
    code = "dependency_service_unavailable"
    status_code = 503
    message = "Dependency service is temporarily unavailable"


class CopyPendingUnsupported(MarketplaceError):
    code = "copy_pending_unsupported"
    status_code = 422
    message = "Copy pending state is not supported"


class CopyFailed(MarketplaceError):
    code = "copy_failed"
    status_code = 422
    message = "Copy operation failed"
