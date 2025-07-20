from fit_ctf.exceptions import CTFBaseException


class CTFModelException(CTFBaseException):
    """Base exception class for all fit_ctf_models errors."""

    pass


class ProjectNamingFormatException(CTFModelException):
    """Given project name does not follow the allowed format."""

    pass


class UsernameFormatException(CTFModelException):
    """Given username does not follow the allowed format."""

    pass


class ProjectNotExistException(CTFModelException):
    """A project with the given name does not exist."""

    pass


class ProjectExistsException(CTFModelException):
    """A project with the given name already exists."""

    pass


class DirNotEmptyException(CTFModelException):
    """A directory with the given path does not exist."""

    pass


class DirNotExistsException(CTFModelException):
    """A directory with the given path already exists."""

    pass


class UserNotExistsException(CTFModelException):
    """A user with the given username does not exist."""

    pass


class UserExistsException(CTFModelException):
    """A user with the given username already exists."""

    pass


class SSHPortOutOfRangeException(CTFModelException):
    """A selected port is out of allowed range."""

    pass


class UserNotEnrolledToProjectException(CTFModelException):
    """A given user is not enrolled to the selected project."""

    pass


class UserEnrolledToProjectException(CTFModelException):
    """A given user is enrolled to the selected project."""

    pass


class MaxUserCountReachedException(CTFModelException):
    """A maximal number of users per project reached."""

    pass


class ContainerPortUsageCollisionException(CTFModelException):
    """A selected container port is already in use."""

    pass


class ForwardedPortUsageCollisionException(CTFModelException):
    """A selected forwarded port is already in use."""

    pass


class ModuleExistsException(CTFModelException):
    """A module with the given name already exists."""

    pass


class ModuleNotExistsException(CTFModelException):
    """A module with the given name does not exist."""

    pass


class ShadowPathNotExistException(CTFModelException):
    """A shadow for of the selected user does not exist."""

    pass


class ServiceNotExistException(CTFModelException):
    """The service with the given name does not exist."""

    pass


class ServiceExistException(CTFModelException):
    """The service with the given name already exists."""

    pass


class ModuleInUseException(CTFModelException):
    """The selected module is still used by some kind of server"""

    pass
