from argon2.exceptions import VerifyMismatchError
from fit_ctf_models.utils.exceptions import UserNotExistsException
import fit_ctf_models.user as user
from fit_ctf_components.auth.auth_interface import AuthInterface

from argon2 import PasswordHasher


class LocalAuth(AuthInterface):

    def __init__(self, user_mgr: "user.UserManager"):
        super().__init__(True)
        self._user_mgr = user_mgr

    def register(self, username: str, password: str) -> str:
        _ = username
        ph = PasswordHasher()
        hash = ph.hash(password)
        return hash

    def validate_credentials(self, username: str, password: str) -> bool:
        try:
            user = self._user_mgr.get_user(username)
            ph = PasswordHasher()
            ph.verify(user.password, password)
        except (UserNotExistsException, VerifyMismatchError):
            return False
        return True
