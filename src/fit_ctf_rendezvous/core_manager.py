import re
from typing import Any, Callable

from fit_ctf.ctf_base import CTFBase
from fit_ctf_components.auth.auth_interface import AuthInterface
from fit_ctf_components.auth.local_auth import LocalAuth
from fit_ctf_components.constants import DEFAULT_PASSWORD_LENGTH
from fit_ctf_components.exceptions import CTFException
from fit_ctf_models.project import Project
from fit_ctf_models.user import User
from fit_ctf_models.user_enrollment import UserEnrollment
from fit_ctf_rendezvous.exceptions import CannotChangePassword

REGEX_IS_LOWER_CASE = re.compile("[a-z]")
REGEX_IS_UPPER_CASE = re.compile("[A-Z]")
REGEX_IS_DIGIT = re.compile("[0-9]")


class _VariableRegistry:
    _active_user: User | None = None
    _selected_project: Project | None = None

    _callbacks: dict[str, dict[str, Callable[[Any | None], None]]] = {
        "active_user": {},
        "selected_project": {},
    }

    @property
    def active_user(self) -> User | None:
        """Get signed user.

        :return: User object if user is signed; `None` otherwise.
        :rtype: User | None
        """
        return self._active_user

    @active_user.setter
    def active_user(self, value: User | None):
        for _, _callback in self._callbacks["active_user"].items():
            _callback(value)
        self._active_user = value

    @property
    def selected_project(self) -> Project | None:
        return self._selected_project

    @selected_project.setter
    def selected_project(self, value: Project | None):
        for _, callback in self._callbacks["selected_project"].items():
            callback(value)
        self._selected_project = value

    def register_hook(
        self, variable_name: str, name: str, callback: Callable[[Any | None], None]
    ):
        self._callbacks[variable_name][name] = callback

    def unregister_hook(self, variable_name: str, name: str):
        self._callbacks[variable_name].pop(name)

    def unregister_from_all(self, name: str):
        for callbacks in self._callbacks.values():
            callbacks.pop(name)


class CoreManager(_VariableRegistry):

    def __init__(self, ctf_base: CTFBase, auth_client: AuthInterface | None = None):
        self._ctf_base = ctf_base
        # TODO: config
        self.auth_client = auth_client if auth_client else LocalAuth(ctf_base.user_mgr)

    @property
    def ctf_base(self) -> CTFBase:
        return self._ctf_base

    def validate_login(self, username: str, password: str) -> bool:
        """Validate user's login attempt.

        :param username: Given username.
        :type username: str
        :param password: Given password.
        :type password: str
        :return: `True` if given credentials are valid; False otherwise.
        :rtype: bool
        """
        if not self.auth_client.validate_credentials(username, password):
            return False

        self._active_user = self.ctf_base.user_mgr.get_doc_by_filter(username=username)
        return True

    @staticmethod
    def check_password_strength(password: str) -> bool:
        """Validate password strength.

        :return: `True` if the password meet all the password requirements.
        :rtype: bool
        """
        return AuthInterface.validate_password_strength(password)

    def generate_password(self) -> str:
        """Generate a basic password.

        :return: New password.
        :rtype: str
        """
        return AuthInterface.generate_password(DEFAULT_PASSWORD_LENGTH)

    def change_password(self, password: str):
        """Change user password.

        :param password: New password.
        :type password: str
        """
        if not self._active_user:
            return
        if not self.auth_client.local_login:
            raise CannotChangePassword(
                "The Auth client does not support password update."
            )
        self.ctf_base.user_mgr.change_password(self._active_user.username, password)

    def get_active_projects(self) -> list[Project]:
        """Get a list of enrolled projects.

        :return: A list of enrolled projects for the given user.
        :rtype: list[Project]
        """
        if not self.active_user:
            return []
        return self.ctf_base.user_enrollment_mgr.get_enrolled_projects(
            self.active_user.username
        )

    async def start_user_instance(self) -> UserEnrollment | None:
        """Start user login nodes.

        :param project_name: Project name.
        :type project_name: str
        :return: Found user enrollment object; `None` otherwise.
        :rtype: UserEnrollment | None
        """
        if not self.active_user or not self.selected_project:
            return None
        try:
            user_enrollment = self.ctf_base.user_enrollment_mgr.get_user_enrollment(
                self.active_user, self.selected_project
            )
        except CTFException:
            # TODO: print e
            return None

        await self.ctf_base.user_enrollment_mgr.start_user_cluster(
            self.active_user, self.selected_project
        )
        return user_enrollment

    async def stop_user_instance(self):
        """Stop user login nodes.

        :param project_name: Project name.
        :type project_name: str
        """
        if not self.active_user or not self.selected_project:
            return

        try:
            self.ctf_base.user_enrollment_mgr.get_user_enrollment(
                self.active_user, self.selected_project
            )
        except CTFException:
            return

        await self.ctf_base.user_enrollment_mgr.stop_user_cluster(
            self.active_user, self.selected_project
        )

    async def instance_is_running(self) -> bool:
        if not self.active_user or not self.selected_project:
            return False
        return await self.ctf_base.user_enrollment_mgr.user_cluster_is_running(
            self.active_user, self.selected_project
        )

    def cleanup(self):
        # TODO: implement shutting down running instances of the user
        pass
