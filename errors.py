"""Provides errors and warnings related to operation of the Path types in this package.

Classes:
    PathError
    IncorrectArgumentsError
    NonexistentMappingError
    PathWarning
    IncorrectFileTypeWarning
    UnsupportedOperationWarning
    UnexpectedSituationWarning
"""


class PathError(Exception):
    """Raised by invalid actions when creating or using Path objects or subclasses."""


class IncorrectArgumentsError(PathError):
    """Raised when a Path object is created with the incorrect set of information to properly do so."""


class NonexistentMappingError(PathError):
    """Raised when a method requiring a filesystem or other mapping is run on a Path object that does not have one."""


class PathWarning(UserWarning):
    """Raised by invalid but correctable actions when creating or using Path objects or subclasses."""


class IncorrectFileTypeWarning(PathWarning):
    """Raised when a binary mode file object is accessed in text mode, or vice versa."""


class UnsupportedOperationWarning(PathWarning):
    """Raised when an invalid but recoverable operation is attempted on a Path object."""


class UnexpectedSituationWarning(PathWarning):
    """Raised to alert the user/developer of a situation that should theoretically not be possible"""