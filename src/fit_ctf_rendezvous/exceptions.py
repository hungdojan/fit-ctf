class FitRendezvousException(Exception):
    pass


class IncorrectCredentials(FitRendezvousException):
    pass


class UserNotLoggedIn(FitRendezvousException):
    pass
