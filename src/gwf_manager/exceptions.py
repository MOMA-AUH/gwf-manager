"""Custom exception hierarchy for gwf-manager."""


class GwfManagerError(Exception):
    """Base exception for gwf-manager."""


class DuplicateTargetError(GwfManagerError):
    """Raised when a target with a differing spec is resubmitted under the same name."""


class TaskNotFoundError(GwfManagerError):
    """Raised when a referenced task does not exist."""


class OutputNotFoundError(GwfManagerError):
    """Raised when a referenced task output does not exist."""


class ConfigurationError(GwfManagerError):
    """Raised for configuration-related errors."""


class TaskOutputError(GwfManagerError):
    """Raised when task outputs are invalid."""
