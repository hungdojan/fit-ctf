import shutil
import warnings
from datetime import datetime
from typing import TYPE_CHECKING

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from passlib.hash import sha512_crypt
from pymongo.collection import Collection
from pymongo.database import Database

from fit_ctf.components.auth.auth_interface import AuthInterface
from fit_ctf.components.constants import DEFAULT_PASSWORD_LENGTH
from fit_ctf.components.container_client.container_client_interface import (
    ContainerClientInterface,
)
from fit_ctf.components.logger.logger_interface import LoggerInterface
from fit_ctf.components.types import NewUserDict, UserInfoDict, UserRole
from fit_ctf.exceptions import CTFBaseException
from fit_ctf.models.base import Base, BaseManagerInterface
from fit_ctf.models.utils.exceptions import (
    PublicKeyUploadFail,
    UserExistsException,
    UserNotExistsException,
)
from fit_ctf.models.utils.mongo_queries import MongoQueries
from fit_ctf.models.utils.repository import EntityRepository
from fit_ctf.models.utils.sessions import LoginSession
from fit_ctf.path_mgmt import PathManagement
from fit_ctf.templates import TEMPLATE_PATH_MAP, get_template

# suppress deprecation warning for `crypt` module used by `passlib` when generating shadow
warnings.filterwarnings("ignore", category=DeprecationWarning, module="passlib")

if TYPE_CHECKING:
    import fit_ctf.models.core.enrollment as enroll
    import fit_ctf.models.infra.user_cluster as user_cluster


class User(Base):
    """A class that represents a user document.

    :param username: A string used to identify a user chosen by the user.
    :type username: str
    :param password: A hashed password used for user authentication.
    :type password: str
    :param role: User role defines account's capabilities.
    :type role: UserRole
    :param shadow_path: A path to the user shadow file.
    :type shadow_path: str
    :param shadow_hash: A hash string that is passed to the shadow file.
    :type shadow_hash: str
    :param email: User email.
    :type email: str
    """

    username: str
    password: str
    role: UserRole
    email: str = ""
    sessions: list[LoginSession] = []

    def record_login_session(self):
        session = LoginSession(
            timestamp=datetime.now().astimezone(), state=LoginSession.State.LOGIN
        )
        self.sessions.append(session)

    def record_logout_session(self):
        session = LoginSession(
            timestamp=datetime.now().astimezone(), state=LoginSession.State.LOGOUT
        )
        self.sessions.append(session)


class UserManager(BaseManagerInterface[User]):
    """A manager class that handles operations with `User` objects."""

    def __init__(
        self,
        db: Database,
        coll: Collection,
        model_cls: type[User],
        repo: EntityRepository,
        user_cluster_mgr: "user_cluster.UserClusterManager",
        c_client: ContainerClientInterface,
        paths: PathManagement,
        logger: LoggerInterface,
    ):
        """Constructor method.

        :param db: A MongoDB database object.
        :type db: Database
        :param coll: MongoDB collection object.
        :type coll: Collection
        :param model_cls: Model class for User.
        :type model_cls: type[User]
        :param enroll_mgr: Enrollment manager instance.
        :type enroll_mgr: EnrollmentManager
        :param user_cluster_mgr: User cluster manager instance.
        :type user_cluster_mgr: UserClusterManager
        :param c_client: Container client interface.
        :type c_client: ContainerClientInterface
        :param paths: Path management instance.
        :type paths: PathManagement
        :param logger: Logger interface.
        :type logger: LoggerInterface
        """
        super().__init__(db, coll, model_cls, c_client, paths, logger)
        self._repo = repo
        self._user_cluster_mgr = user_cluster_mgr

    def get_user(self, user_or_username: str | User, active: bool | None = True) -> User:
        """Retrieve a user from the database.

        :param user_or_username: User username or user object.
        :type user_or_username: str | User
        :param active: Fetch documents with the given active value. If set to None,
            the function fetches both active and inactive documents. Defaults to True.
        :type active: bool | None
        :raises UserNotExistsException: User with the given username was not found.
        :return: A found user object.
        :rtype: User
        """
        if isinstance(user_or_username, User):
            return user_or_username
        username = user_or_username
        _filter: dict = {"username": username}
        if active is not None:
            _filter["active"] = active
        user = self.get_doc_by_filter(**_filter)
        if not user:
            raise UserNotExistsException(f"User `{username}` does not exist.")
        return user

    def get_user_raw(self, user_or_username: str | User) -> dict:
        """Return a dictionary of a user object.

        :param user_or_username: A username or a User object.
        :type user_or_username: str | User
        :return: A user object in dict format.
        :rtype: dict
        """
        user = self.get_user(user_or_username)
        user = user.model_dump()
        user.pop("password", "")
        user.pop("_id", "")
        return user

    @staticmethod
    def _generate_shadow(username: str, password: str, shadow_path: str) -> str:
        """Generate a shadow hash.

        The function both calculates shadow hash and generated the shadow file.

        :param username: User username.
        :type username: str
        :param password: User password (NOT its hash digest).
        :type password: str
        :param shadow_path: Path to the destination file where the shadow file will be
            written.
        :type shadow_path: str
        :return: Calculated shadow hash.
        :rtype: str
        """
        crypt_hash = sha512_crypt.using(rounds=20000).hash(password)
        template = get_template("shadow.j2", str(TEMPLATE_PATH_MAP["jinja_template"].resolve()))
        with open(f"{shadow_path}", "w") as f:
            f.write(template.render(hash=crypt_hash))
        return crypt_hash

    @staticmethod
    def generate_password_hash(password):
        ph = PasswordHasher()
        hash = ph.hash(password)
        return hash

    @staticmethod
    def validate_password(user: User, password: str) -> bool:
        try:
            ph = PasswordHasher()
            ph.verify(user.password, password)
        except VerifyMismatchError:
            return False
        return True

    def record_login(self, user: User):
        user.record_login_session()
        self.update_doc(user)

    def record_logout(self, user: User):
        user.record_logout_session()
        self.update_doc(user)

    def change_password(self, username: str, password: str) -> User:
        """Change password for a user.

        Update password hash in the database and user's shadow file content.

        :param username: User username.
        :type username: str
        :param password: User password.
        :type password: str
        :raises UserNotExistsException: Given user could not be found in the database.
        :return: Updated `User` object.
        :rtype: User
        """
        user = self.get_user(username)
        shadow_path = self.paths.user_path(user) / "shadow"

        # calculate and update hash for shadow
        self.logger.debug(f"Updating `{shadow_path.resolve()}`")
        self._generate_shadow(user.username, password, str(shadow_path.resolve()))

        # calculate hash to store to the database
        user.password = self.generate_password_hash(password)

        self.update_doc(user)
        return user

    def create_new_user(
        self,
        username: str,
        password: str,
        role: UserRole = UserRole.USER,
        email: str = "",
        **kw,
    ) -> tuple[User, NewUserDict]:
        """Create a new user.

        If user already exists function will raise an exception.

        :param username: User's username.
        :type username: str
        :param password: User's password.
        :type password: str
        :param role: User's role. Defaults to `user`.
        :type role: UserRole
        :param email: User's email. Defaults to "".
        :type email: str
        :raises UserExistsException: A user with given `username` already exists.
        :return: Newly created user object and a directory containing
            `username` and `password` in plain-text format.
        :rtype: tuple[User, dict[str, str]]
        """
        # TODO: activate inactive user
        user = self.get_doc_by_filter(username=username, active=True)
        if user:
            raise UserExistsException(f"User `{username}` already exists.")

        root_dir = self.paths.user_path(username)
        root_dir.mkdir(parents=True)
        shadow_file = root_dir / "shadow"
        home_dir = root_dir / "home"
        home_dir.mkdir(parents=True, mode=0o777)
        # mkdir() still applies the process umask; chmod forces bind-mount-friendly perms
        home_dir.chmod(0o777)

        # generate shadow from file
        self.logger.debug(f"Generating `{str(shadow_file.resolve())}`")
        self._generate_shadow(username, password, str(shadow_file.resolve()))

        user = self.create_and_insert_doc(
            username=username,
            password=self.generate_password_hash(password),
            role=role,
            email=email,
            sessions=[],
        )
        return user, {"username": username, "password": password}

    def create_multiple_users(
        self,
        lof_usernames: list[str],
        default_password: str | None = None,
    ) -> list[NewUserDict]:
        """Generate new users from the given list of usernames.

        Ignores usernames that already has an account.

        :param lof_usernames: List of usernames.
        :type lof_usernames: list[str]
        :param default_password: A default password that will be set to all new users.
            If set to None, the password will be randomly generated. Defaults to None.
        :type default_password: str | None
        :return: A list of usernames and passwords in plain-text format (not a hash) objects.
        :rtype: list[NewUserDict]
        """
        # eliminate duplicates
        existing_users = [
            u["username"]
            for u in self.get_docs_raw(
                filter={"username": {"$in": lof_usernames}},
                projection={"_id": 0, "username": 1},
            )
        ]

        new_usernames = set(lof_usernames).difference(set(existing_users))
        password = (
            default_password
            if default_password is not None
            else AuthInterface.generate_password(DEFAULT_PASSWORD_LENGTH)
        )
        # generate random passwords for each new user
        lof_user_info = {username: password for username in new_usernames}
        users = []

        # create new users
        for username, password in lof_user_info.items():
            _, data = self.create_new_user(username, password)
            users.append(data)

        return users

    def upload_public_key(self, user_or_username: User | str, pub_key: bytes):
        """Upload public SSH key to `authorized_keys` file.

        :param user_or_username: User username or user object.
        :type user_or_username: str | User
        :param pub_key: Raw public key bytes.
        :type pub_key: bytes
        :raise PublicKeyUploadFail: When the given key data is not correct.
        """
        try:
            serialization.load_ssh_public_key(pub_key)
        except (ValueError, UnsupportedAlgorithm) as e:
            raise PublicKeyUploadFail(e)

        # create required file
        ssh_dirpath = self.paths.user_path(user_or_username) / "home" / ".ssh"
        ssh_dirpath.mkdir(parents=True, exist_ok=True)
        ssh_dirpath.chmod(0o700)
        authorized_keys_file = ssh_dirpath / "authorized_keys"

        # read content and then rewrite it
        # not the fastest way to add a key
        key_set = set()
        if authorized_keys_file.exists():
            key_set = set(authorized_keys_file.read_bytes().splitlines())
        key_set.add(pub_key)
        with open(authorized_keys_file, "wb") as f:
            f.writelines(key_set)
        authorized_keys_file.chmod(0o600)

    def get_users_info(self, active: bool | None = None) -> list[UserInfoDict]:
        """Get list of all users.

        Creates a query that look up all users in the database and their assigned project
        names.

        :param active: Fetch documents with the given active value. If set to None,
            the function fetches both active and inactive documents. Defaults to True.
        :type active: bool | None
        :return: A list of users with additional information.
        :rtype: list[UserInfoDict]
        """
        pipeline = MongoQueries.user_get_users(active)
        return [i for i in self.collection.aggregate(pipeline)]

    async def disable_user(self, username: str, enroll_mgr: "enroll.EnrollmentManager"):
        """Set user as inactive in the database.

        The user data and files will be preserve for future references.
        :param username: User's username.
        :type username: str
        :param enroll_mgr: Enrollment manager for enrollment operations.
        :type enroll_mgr: EnrollmentManager
        """
        user = self.get_user(username)

        lof_projects = enroll_mgr.get_enrolled_projects(user.username)
        for project in lof_projects:
            try:
                enrollment = enroll_mgr.get_enrollment(user, project)
                cluster = self._user_cluster_mgr.get_cluster(enrollment)
                await self._user_cluster_mgr.stop_cluster(cluster, enroll_mgr)
            except CTFBaseException:  # pragma: no cover
                pass  # Cluster doesn't exist or already stopped

        await enroll_mgr.cancel_user_from_all_projects(user)
        user.active = False
        self.update_doc(user)

    def flush_user(self, username: str):
        """Completely remove user data from the host machine.

        Only works if the user is not active.

        :param username: User's username.
        :type username: str
        :raises UserExistsException: When the user document is still active.
        """
        try:
            user = self.get_user(username, None)
            if user.active:
                raise UserExistsException("Cannot flush files of an active user.")
        except UserNotExistsException as e:
            raise UserNotExistsException(e)

        path = self.paths.user_path(username)
        if path.exists():
            shutil.rmtree(path)
        self.remove_doc_by_id(user.id)

    async def disable_multiple_users(
        self, lof_usernames: list[str], enroll_mgr: "enroll.EnrollmentManager"
    ):
        """Disables multiple user documents.

        :param lof_usernames: A list of usernames which documents will be disabled.
        :type lof_usernames: list[str]
        :param enroll_mgr: Enrollment manager for enrollment operations.
        :type enroll_mgr: EnrollmentManager
        """
        users = self.get_docs(username={"$in": lof_usernames}, active=True)
        user_ids = [u.id for u in users]

        pairs = []
        for user in users:
            await self._user_cluster_mgr.stop_all_clusters_of_a_user(user, enroll_mgr)
            pairs.extend([(user, prj) for prj in enroll_mgr.get_enrolled_projects(user)])

        await enroll_mgr.disable_multiple_enrollments(pairs)
        self.collection.update_many({"_id": {"$in": user_ids}}, {"$set": {"active": False}})

    async def flush_multiple_users(
        self, lof_usernames: list[str], enroll_mgr: "enroll.EnrollmentManager"
    ):
        """Remove multiple user data from the host machine.

        Only works if the user is not active.

        :param lof_username: A list of usernames.
        :type lof_usernames: list[str]
        :param enroll_mgr: Enrollment manager for enrollment operations.
        :type enroll_mgr: EnrollmentManager
        :raises UserExistsException: When the user document is still active.
        """
        users = self.get_docs(username={"$in": lof_usernames}, active=False)

        pairs = []
        for user in users:
            pairs.extend([(user, prj) for prj in enroll_mgr.get_enrolled_projects(user, True)])
            path = self.paths.user_path(user)
            if path.exists():
                shutil.rmtree(path)

        await enroll_mgr.flush_multiple_enrollments(pairs)
        self.remove_docs_by_id([u.id for u in users])

    async def delete_a_user(self, username: str, enroll_mgr: "enroll.EnrollmentManager"):
        """Completely remove user from the host machine.

        :param username: Account's username.
        :type username: str
        :param enroll_mgr: Enrollment manager.
        :type enroll_mgr: EnrollmentManager
        :raises UserNotExistsException: Given user could not be found in the database.
        """
        await self.disable_user(username, enroll_mgr)
        self.flush_user(username)

    async def delete_users(self, lof_usernames: list[str], enroll_mgr: "enroll.EnrollmentManager"):
        """Deletes users from the list.

        :param lof_usernames: List of usernames to delete.
        :type lof_usernames: list[str]
        :param enroll_mgr: Enrollment manager.
        :type enroll_mgr: EnrollmentManager
        """

        await self.disable_multiple_users(lof_usernames, enroll_mgr)
        await self.flush_multiple_users(lof_usernames, enroll_mgr)

    async def delete_all(self, enroll_mgr: "enroll.EnrollmentManager"):
        """Remove all users from the host system and clear the database.

        :param enroll_mgr: Enrollment manager.
        :type enroll_mgr: EnrollmentManager
        """

        users = [u.username for u in self.get_docs()]
        await self.delete_users(users, enroll_mgr)
