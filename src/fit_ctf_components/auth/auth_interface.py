import re
import secrets
import string
from abc import ABC, abstractmethod


class AuthInterface(ABC):

    def __init__(self, local_login: bool) -> None:
        self._local_login = local_login

    @property
    def local_login(self) -> bool:
        return self._local_login

    @staticmethod
    def generate_password(len: int) -> str:
        """Generate a random password.

        :param len: The length of the final password.
        :type len: int
        :raises ValueError: The `len` value cannot be less than 0.
        :return: Generated password.
        :rtype: str
        """
        if len < 0:
            raise ValueError("The length of the password cannot be less than 0.")
        alphabet = string.ascii_letters + string.digits
        password = "".join(secrets.choice(alphabet) for _ in range(len))
        return password

    @staticmethod
    def validate_password_strength(password: str) -> bool:
        """Check if the password is strong enough.

        Strong password is at least 8 characters long, has at least one upper,
        lower character and a digit.

        :param password: Password to validate.
        :type password: str
        :return: `True` if password meets all the criteria.
        :rtype: bool
        """
        return re.search(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d).{8,}$", password) is not None

    @staticmethod
    def validate_username_format(username: str) -> bool:
        """Validate the username format.

        The username must be at least 4 characters long and can only contain lowercase
        characters, or digits.

        :param username: A username to validate.
        :type username: str
        :return: `True` if username meets all the criteria.
        :rtype: bool
        """
        return re.search(r"^[a-z0-9]{4,}$", username) is not None

    @abstractmethod
    def register(self, username: str, password: str) -> str:
        """Register user.

        :param username: Account's username.
        :type username: str
        :param password: Account's password.
        :type password: str
        :return: Hashed password or token.
        :rtype: str
        """
        raise NotImplementedError()

    @abstractmethod
    def validate_credentials(self, username: str, password: str) -> bool:
        """Validate user credentials.

        :param username: Account's username.
        :type username: str
        :param password: Account's password.
        :type password: str
        :return: True if the validation succeeds.
        :rtype: bool
        """
        raise NotImplementedError()
