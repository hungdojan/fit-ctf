import fit_ctf_models.user as user
from fit_ctf_components.auth.auth_interface import AuthInterface
from fit_ctf_components.exceptions import LoginException
from fit_ctf_models.utils.exceptions import UserNotExistsException


class LocalAuth(AuthInterface):

    def __init__(self, user_mgr: "user.UserManager"):
        super().__init__(True)
        self._user_mgr = user_mgr

    def validate_credentials(self, username: str, password: str) -> user.User:
        error_msg = "Incorrect login credentials."
        try:
            user = self._user_mgr.get_user(username)
        except UserNotExistsException:
            raise LoginException(error_msg)
        if not self._user_mgr.validate_password(user, password):
            raise LoginException(error_msg)
        return user
