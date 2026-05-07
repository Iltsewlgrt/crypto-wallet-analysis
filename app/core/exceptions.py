class WalletAnalyzerError(Exception):
    """Base exception for the application."""


class ExternalApiError(WalletAnalyzerError):
    """Raised when blockchain API call fails."""


class ValidationError(WalletAnalyzerError):
    """Raised when user input is invalid."""


class PersistenceError(WalletAnalyzerError):
    """Raised when writing files fails."""
