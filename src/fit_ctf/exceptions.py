class CTFBaseException(BaseException):
    """Base exception for all fit-ctf errors."""

    pass


class CTFAppException(CTFBaseException):
    """Base exception for all fit-ctf-cli app errors."""

    pass


class ManagerNotFound(CTFAppException):
    pass


class ImportFileCorruptedException(CTFAppException):
    """All the errors that occur during project import."""

    pass
