from fit_ctf.exceptions import CTFBaseException


class CTFComponentException(CTFBaseException):
    """Base CTF exception class."""

    pass


class ValidatorNotExistException(CTFBaseException):
    """A validator with given name does not exist."""

    pass


class SchemaFileNotExistException(CTFBaseException):
    """A schema file could not be located."""

    pass


class DataFileNotExistException(CTFBaseException):
    """A configuration file could not be located."""

    pass


class DataValidationErrorException(CTFBaseException):
    """A provided file is not syntactically correct."""

    pass


class ConfigurationFileNotEditedException(CTFBaseException):
    """The configuration data were not edited in the editor."""

    pass
