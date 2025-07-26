class TechnicalException(Exception):
    """Base class for technical exceptions."""
    pass

class InvalidConfigurationException(TechnicalException):
    """Raised when there is an invalid configuration."""
    pass
