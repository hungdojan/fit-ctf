class FitRendezvousException(Exception):
    pass


class IncorrectCredentials(FitRendezvousException):
    pass


class UserNotLoggedIn(FitRendezvousException):
    pass


class CannotChangePassword(FitRendezvousException):
    pass


class InconsistentState(FitRendezvousException):
    pass


class InvalidAction(FitRendezvousException):
    pass


class SecretSubmitFail(FitRendezvousException):
    pass
