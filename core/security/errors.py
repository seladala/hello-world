"""Security exception hierarchy."""


class SecurityViolation(Exception):
    """Base class for every reason the program may refuse to greet you."""


class IntegrityViolation(SecurityViolation):
    pass


class CheatDetected(SecurityViolation):
    pass


class LicenseError(SecurityViolation):
    pass
