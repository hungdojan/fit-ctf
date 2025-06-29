import fit_ctf_models.user as user
from fit_ctf_components.auth.auth_interface import AuthInterface
from fit_ctf_components.exceptions import UserNotExistsException


class LocalAuth(AuthInterface):

    def __init__(self, user_mgr: "user.UserManager"):
        super().__init__(True)
        self._user_mgr = user_mgr

    def validate_credentials(self, username: str, password: str) -> bool:
        try:
            user = self._user_mgr.get_user(username)
        except UserNotExistsException:
            return False
        return user.password == self.get_password_hash(password)
