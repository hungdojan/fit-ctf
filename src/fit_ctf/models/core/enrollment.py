import shutil
from typing import Any

from bson import DBRef
from pymongo.collection import Collection
from pymongo.database import Database

import fit_ctf.models.core.project as _project
import fit_ctf.models.core.user as _user
import fit_ctf.models.infra.project_cluster as project_cluster
import fit_ctf.models.infra.user_cluster as user_cluster
from fit_ctf.components.container_client.container_client_interface import (
    ContainerClientInterface,
)
from fit_ctf.components.logger.logger_interface import LoggerInterface
from fit_ctf.components.types import (
    LeaderBoardItem,
    RawEnrolledProjectsDict,
)
from fit_ctf.components.utils import get_missing_in_sequence
from fit_ctf.models.base import Base, BaseManager
from fit_ctf.models.core.user_progress import UserProgress, UserProgressManager
from fit_ctf.models.infra.utils import count_submittable_secret_slots
from fit_ctf.models.utils.exceptions import (
    ContainerPortUsageCollisionException,
    ForwardedPortUsageCollisionException,
    MaxUserCountReachedException,
    ProjectClusterNotExistException,
    ProjectNotExistException,
    SSHPortOutOfRangeException,
    UserEnrolledToProjectException,
    UserNotEnrolledToProjectException,
    UserNotExistsException,
)
from fit_ctf.models.utils.mongo_queries import MongoQueries
from fit_ctf.models.utils.repository import EntityRepository
from fit_ctf.models.utils.sessions import ProgressSession
from fit_ctf.path_mgmt import PathManagement


class Enrollment(Base):
    """A class that represents an enrollment document.

    It serves as a connection between the project and a user or team. When a user or team
    enrolls to a project, a new `enrollment` document is created.

    :param user_id: A reference object that indicates a connection between a user and this
        document.
    :type user_id: DBRef
    :param project_id: A reference object that indicates a connection between a project
        and this document.
    :type project_id: DBRef
    :param container_port: An SSH port used to connect to login node.
    :type container_port: int
    :param forwarded_port: A forwarded port that user will connect to the outer server.
    :type forwarded_port: int
    :param modules: A collection of active modules that will start together with login
        node.
    :type modules: dict[str, Module]
    """

    project_id: DBRef
    container_port: int
    forwarded_port: int
    progress: UserProgress
    user_id: DBRef
    # team_id: DBRef | None = None


class EnrollmentManager(BaseManager[Enrollment], UserProgressManager):
    """A manager class that handles operations with `Enrollment` objects."""

    def __init__(
        self,
        db: Database,
        coll: Collection,
        model_cls: type[Enrollment],
        repo: EntityRepository,
        user_cluster_mgr: "user_cluster.UserClusterManager",
        project_cluster_mgr: "project_cluster.ProjectClusterManager",
        c_client: ContainerClientInterface,
        paths: PathManagement,
        logger: LoggerInterface,
    ):
        """Constructor method.

        :param db: A MongoDB database object.
        :type db: Database
        :param coll: MongoDB collection object.
        :type coll: Collection
        :param model_cls: Model class for Enrollment.
        :type model_cls: type[Enrollment]
        :param repo: Shared entity repository.
        :type repo: EntityRepository
        :param user_cluster_mgr: User cluster manager instance.
        :type user_cluster_mgr: UserClusterManager
        :param project_cluster_mgr: Project cluster manager instance.
        :type project_cluster_mgr: ProjectClusterManager
        :param c_client: Container client interface.
        :type c_client: ContainerClientInterface
        :param paths: Path management instance.
        :type paths: PathManagement
        :param logger: Logger interface.
        :type logger: LoggerInterface
        """
        BaseManager.__init__(self, db, coll, model_cls, c_client, paths, logger)
        UserProgressManager.__init__(self, user_cluster_mgr, project_cluster_mgr)
        self._repo = repo
        self._user_cluster_mgr = user_cluster_mgr
        self._project_cluster_mgr = project_cluster_mgr

    def _get_user_and_project(
        self,
        user_or_username: "str | _user.User",
        project_or_name: "str | _project.Project",
    ) -> tuple["_user.User", "_project.Project"]:
        """Retrieve both `User` and `Project` objects.

        :param user_or_username: User username or user object.
        :type user_or_username: str | _user.User
        :param project_or_name: Project name or project object.
        :type project_or_name: str | _project.Project
        :raises UserNotExistsException: User with the given username was not found.
        :raises ProjectNotExistException: Project data was not found in the database.
        :return: A found pair of `User` and `Project` objects.
        :rtype: tuple[_user.User, _project.Project]
        """
        return self._get_user(user_or_username), self._get_project(project_or_name)

    def _get_user(self, user_or_username: "str | _user.User") -> "_user.User":
        """Get a user from the username or user object.

        :param user_or_username: Username or a user object.
        :type user_or_username: str | _user.User
        :raises UserNotExistsException: User with the given username was not found.
        :return: User with the given name, or the same object that was passed into the
            function.
        :rtype: _user.User
        """
        return self._repo.get_user(user_or_username)

    def _get_project(self, project_or_name: "str | _project.Project") -> "_project.Project":
        """Get a project from the project name or project object.

        :param project_or_name: Project name or a project object.
        :type project_or_name: str | _project.Project
        :raises ProjectNotExistException: Project data was not found in the database.
        :return: Found project or passed project object.
        :rtype: _project.Project
        """
        return self._repo.get_project(project_or_name)

    def user_is_enrolled_to_project(self, user: "_user.User", project: "_project.Project") -> bool:
        """Check if user is enrolled to the given project.

        :param user: User object.
        :type user: str
        :param project: Project object.
        :type project: str
        :return: `True` if there is an enrollment document that links the project with
            the given user.
        :rtype: bool
        """
        enrollment = self.get_doc_by_filter(
            **{"user_id.$id": user.id, "project_id.$id": project.id, "active": True}
        )
        return enrollment is not None

    def get_enrollment(
        self,
        user: "_user.User",
        project: "_project.Project",
        active: bool | None = True,
    ) -> Enrollment:
        """Get an enrollment document.

        :param user: User object.
        :type user: _user.User
        :param project: Project object.
        :type project: _project.Project
        :raises UserNotEnrolledToProjectException: Given user is not enrolled to the
            project.
        :return: The found enrollment document.
        :rtype: Enrollment
        """
        _filter: dict[str, Any] = {
            "user_id.$id": user.id,
            "project_id.$id": project.id,
        }
        if active is not None:
            _filter.update({"active": active})
        enrollment = self.get_doc_by_filter(**_filter)
        if not enrollment:
            raise UserNotEnrolledToProjectException(
                f"User `{user.username}` is not assigned to the project `{project.name}`."
            )
        return enrollment

    def get_used_ports(self, project: "_project.Project") -> list[int]:
        """Retrieve a list of container ports allocated by the users enrolled to the project.

        :param project: A selected project in question.
        :type project: _project.Project
        :return: A list of used ports.
        :rtype: list[int]
        """
        enrollments = self._coll.find(
            filter={"project_id.$id": project.id},
            projection={"_id": 0, "container_port": 1},
        ).sort({"container_port": 1})
        return [uc["container_port"] for uc in enrollments]

    def get_all_forwarded_ports(self, project: "_project.Project | None") -> list[int]:
        """Retrieve a list of forwarded ports allocated by the users enrolled to the project.

        :param project: A selected project in question.
        :type project: _project.Project
        :return: A list of allocated forwarding ports.
        :rtype: list[int]
        """
        pipeline = MongoQueries.enrollment_get_forwarded_ports(project)
        return [i["forwarded_ports"] for i in self.collection.aggregate(pipeline)][0]

    def filter_users_not_in_project(
        self, project_or_name: "str | _project.Project", lof_usernames: list[str]
    ) -> list[str]:
        """Return list of new usernames.

        Makes a difference between the given data and real data.

        :param project_or_name: Project name or instance in question.
        :type project_or_name: str | _project.Project
        :param lof_usernames: A list of username to check against.
        :type lof_usernames: list[str]
        :return: A list of usernames that were not found in the database.
        :rtype: list[str]
        """
        prj = self._get_project(project_or_name)
        users = self.get_enrollments_for_project(prj)
        return list(set(lof_usernames).difference(set([user.username for user in users])))

    # ASSIGN USER TO PROJECTS

    def enroll_user_to_project(
        self,
        user_or_username: "str | _user.User",
        project_or_name: "str | _project.Project",
        container_port: int = -1,
        forwarded_port: int = -1,
        create_login_node: bool = False,
        login_node_type: str | None = None,
    ) -> Enrollment:
        """Enroll user to the project.

        :param username: User username or instance in question.
        :type username: str | _user.User
        :param project_or_name: Project name or instance in question.
        :type project_or_name: str | _project.Project
        :param container_port: An SSH port of the login node. If set to `-1` the function will
            autogenerate a value. Defaults to -1.
        :type container_port: int, optional
        :param forwarded_port: A forwarded port for the user to connect to the outer
            server. If set to `-1` the function will autogenerate a value. Defaults to -1.
        :type forwarded_port: int, optional
        :param create_login_node: Whether to create a login node for the user. Defaults to False.
        :type create_login_node: bool, optional
        :param login_node_type: The type of login node to create (ssh_debian or ssh_ubi).
            Only used if create_login_node is True. Defaults to None.
        :type login_node_type: str | None, optional
        :raises UserNotExistsException: User with the given username was not found.
        :raises ProjectNotExistException: Project data was not found in the database.
        :raise UserEnrolledToProjectException: The user is already enrolled to the project.
        :raises MaxUserCountReachedException: Project has already reached the maximum
            number of enrolled users.
        :raises PortUsageCollisionException: The port is already in use.
        :return: A created `Enrollment` object.
        :rtype: Enrollment
        """
        user, project = self._get_user_and_project(user_or_username, project_or_name)
        users = self.get_enrollments_for_project_raw(project)
        enrollment = self.get_doc_by_filter(
            **{"user_id.$id": user.id, "project_id.$id": project.id, "active": True}
        )

        if enrollment:
            raise UserEnrolledToProjectException(
                f"The user `{user.username}` is already enrolled to `{project.name}`"
            )

        if len(users) >= project.max_nof_users:
            raise MaxUserCountReachedException(
                f"Project `{project.name}` has already reached the maximum number of users."
            )

        # checking container ports
        used_container_ports = self.get_used_ports(project)
        if container_port < 0:
            container_port = get_missing_in_sequence(
                used_container_ports, project.starting_port_bind
            )
        elif container_port in used_container_ports:
            raise ContainerPortUsageCollisionException("Selected port is already in used.")
        elif container_port < project.starting_port_bind or container_port > project.max_port:
            raise SSHPortOutOfRangeException(
                "The container port must be in range "
                f"{project.starting_port_bind} and {project.max_port}."
            )

        # checking forwarded ports
        if forwarded_port < 0:
            forwarded_port = container_port
        elif forwarded_port in self.get_all_forwarded_ports(None):
            raise ForwardedPortUsageCollisionException("The forwarded port is already in used.")
        elif forwarded_port < 1 or forwarded_port > 65_535:
            raise SSHPortOutOfRangeException("Forwarded port must be in range 1 to 65 535.")

        self.paths.enrolled_user_path(user, project).mkdir(parents=True)
        enrollment = self.create_and_insert_doc(
            user_id=DBRef("user", user.id),
            project_id=DBRef("project", project.id),
            container_port=container_port,
            forwarded_port=forwarded_port,
            progress=UserProgress(),
        )

        if create_login_node:
            self._user_cluster_mgr.create_cluster(
                self._user_cluster_mgr.create_base_user_cluster(
                    project, user, enrollment, login_node_type=login_node_type
                )
            )
        else:
            self._user_cluster_mgr.create_cluster(
                user_cluster.UserCluster.Builder(
                    user_cluster.UserCluster.Builder.generate_cluster_name(project, user),
                    enrollment,
                ).build()
            )
        n_map = self._user_cluster_mgr.get_network_map((user, project))
        self.c_client.create_networks(project.name, [n_map["private"]])

        return enrollment

    def enroll_multiple_users_to_project(
        self,
        lof_usernames: list[str],
        project_name: str,
        user_mgr: "_user.UserManager",
        create_login_node: bool = False,
        login_node_type: str | None = None,
    ) -> list[Enrollment]:
        """Enroll multiple users to the project.

        :param lof_usernames: A list of usernames.
        :type lof_usernames: list[str]
        :param project_name: Project name.
        :type project_name: str
        :param create_login_node: Whether to create a login node for each user. Defaults to False.
        :type create_login_node: bool, optional
        :param login_node_type: The type of login node to create (ssh_debian or ssh_ubi).
            Only used if create_login_node is True. Defaults to None.
        :type login_node_type: str | None, optional
        :raises ProjectNotExistException: Project with the given name does not exist.
        :raises MaxUserCountReachedException: Project has already reached the maximum
            number of enrolled users.
        :raises PortUsageCollisionException: The port is already in use.
        :return: A list of generated enrollments.
        :rtype: list[Enrollment]
        """
        # check project existence
        project = self._repo.get_project(project_name)

        nof_existing_users = len(self.get_enrollments_for_project_raw(project))
        new_users = self.filter_users_not_in_project(project, lof_usernames)
        if nof_existing_users + len(new_users) > project.max_nof_users:
            raise MaxUserCountReachedException(
                f"Project `{project.name}` has already reached the maximum number of users."
            )

        # get all the ports that can be used
        ports = self.get_used_ports(project)
        all_ports = [project.starting_port_bind + i for i in range(project.max_nof_users)]
        available_ports = sorted(list(set(all_ports).difference(set(ports))))

        users = user_mgr.get_docs(username={"$in": new_users}, active=True)
        enrollments = []
        for i, user in enumerate(users):
            self.paths.enrolled_user_path(user, project).mkdir(parents=True)
            enrollment = Enrollment(
                user_id=DBRef("user", user.id),
                project_id=DBRef("project", project.id),
                container_port=available_ports[i],
                forwarded_port=available_ports[i],
                progress=UserProgress(),
            )
            enrollments.append(enrollment)

        # Batch insert enrollments
        self._coll.insert_many([uc.model_dump() for uc in enrollments])

        for enrollment in enrollments:
            user = self._repo.get_user_by_id(enrollment.user_id.id)
            if not user:
                continue

            if create_login_node:
                self._user_cluster_mgr.create_cluster(
                    self._user_cluster_mgr.create_base_user_cluster(
                        project, user, enrollment, login_node_type=login_node_type
                    )
                )
            else:
                self._user_cluster_mgr.create_cluster(
                    user_cluster.UserCluster.Builder(
                        user_cluster.UserCluster.Builder.generate_cluster_name(project, user),
                        enrollment,
                    ).build()
                )
            n_map = self._user_cluster_mgr.get_network_map((user, project))
            self.c_client.create_networks(project.name, [n_map["private"]])

        return enrollments

    def import_enrollment(
        self,
        user_or_username: "str | _user.User",
        project_or_name: "str | _project.Project",
        progress: UserProgress,
        container_port: int = -1,
        forwarded_port: int = -1,
    ) -> Enrollment:
        """Enroll user to the project.

        :param username: User username or instance in question.
        :type username: str | _user.User
        :param project_or_name: Project name or instance in question.
        :type project_or_name: str | _project.Project
        :param container_port: An SSH port of the login node. If set to `-1` the function will
            autogenerate a value. Defaults to -1.
        :type container_port: int, optional
        :param forwarded_port: A forwarded port for the user to connect to the outer
            server. If set to `-1` the function will autogenerate a value. Defaults to -1.
        :type forwarded_port: int, optional
        :raises UserNotExistsException: User with the given username was not found.
        :raises ProjectNotExistException: Project data was not found in the database.
        :raise UserEnrolledToProjectException: The user is already enrolled to the project.
        :raises MaxUserCountReachedException: Project has already reached the maximum
            number of enrolled users.
        :raises PortUsageCollisionException: The port is already in use.
        :return: A created `Enrollment` object.
        :rtype: Enrollment
        """
        # FIXME:
        user, project = self._get_user_and_project(user_or_username, project_or_name)
        users = self.get_enrollments_for_project_raw(project)
        enrollment = self.get_doc_by_filter(
            **{"user_id.$id": user.id, "project_id.$id": project.id, "active": True}
        )

        if enrollment:
            raise UserEnrolledToProjectException(
                f"The user `{user.username}` is already enrolled to `{project.name}`"
            )

        if len(users) >= project.max_nof_users:
            raise MaxUserCountReachedException(
                f"Project `{project.name}` has already reached the maximum number of users."
            )

        # checking container ports
        used_container_ports = self.get_used_ports(project)
        if container_port < 0:
            container_port = get_missing_in_sequence(
                used_container_ports, project.starting_port_bind
            )
        elif container_port in used_container_ports:
            raise ContainerPortUsageCollisionException("Selected port is already in used.")
        elif container_port < project.starting_port_bind or container_port > project.max_port:
            raise SSHPortOutOfRangeException(
                "The container port must be in range "
                f"{project.starting_port_bind} and {project.max_port}."
            )

        # checking forwarded ports
        if forwarded_port < 0:
            forwarded_port = container_port
        elif forwarded_port in self.get_all_forwarded_ports(None):
            raise ForwardedPortUsageCollisionException("The forwarded port is already in used.")
        elif forwarded_port < 1 or forwarded_port > 65_535:
            raise SSHPortOutOfRangeException("Forwarded port must be in range 1 to 65 535.")

        self.paths.enrolled_user_path(user, project).mkdir(parents=True)

        enrollment = self.create_and_insert_doc(
            user_id=DBRef("user", user.id),
            project_id=DBRef("project", project.id),
            container_port=container_port,
            forwarded_port=forwarded_port,
            progress=progress,
        )
        return enrollment

    # LIST ENROLLMENTS

    def get_enrollments_for_project(
        self, project_or_name: "str | _project.Project", include_inactive: bool = False
    ) -> list["_user.User"]:
        """Return list of users that are enrolled to the project.

        :param project_or_name: Project name or a `Project` object.
        :type project_or_name: str | Project
        :param include_inactive: Search for enrollments that are not active as well.
            Defaults to False.
        :type include_inactive: bool
        :raises ProjectNotExistException: Project data was not found in the database.
        :return: A list of enrolled users.
        :rtype: list[_user.User]
        """
        project = self._get_project(project_or_name)
        pipeline = MongoQueries.enrollment_get_enrolled_users(project, include_inactive)
        return [_user.User(**item) for item in self._coll.aggregate(pipeline)]

    def get_enrollments_for_project_raw(
        self, project_or_name: "str | _project.Project", include_inactive: bool = False
    ) -> list[dict]:
        """Return list of users that are enrolled to the project.

        Returns a raw format of the output. The final dictionary has the following format:
            {
                **{
                    user data without password information
                },
                "forwarded_port": <forwarded_port>,
                "mount": <path_to_mount>
            }

        :param project_or_name: Project name or a `Project` object.
        :type project_or_name: str | Project
        :param include_inactive: Search for enrollments that are not active as well.
            Defaults to False.
        :type include_inactive: bool
        :raises ProjectNotExistException: Project data was not found in the database.
        :return: A list of raw results.
        :rtype: list[dict]
        """
        project = self._get_project(project_or_name)
        pipeline = MongoQueries.enrollment_get_enrolled_users_raw(project, include_inactive)
        return [
            {
                **item["users"],
                "mount": str((self.paths.user_path(item["users"]["username"]) / "home").resolve()),
                "forwarded_port": item["forwarded_port"],
            }
            for item in self.collection.aggregate(pipeline)
        ]

    def get_enrolled_projects(
        self, user_or_username: "str | _user.User", include_inactive: bool = False
    ) -> list["_project.Project"]:
        """Return list of projects that a user has enrolled to.

        :param username: User username.
        :type username: str
        :param include_inactive: Search for enrollments that are not active as well.
            Defaults to False.
        :type include_inactive: bool
        :raises UserNotExistsException: Given user could not be found in the database.
        :return: A list of enrolled projects for the given user.
        :rtype: list[_project.Project]
        """
        user = self._get_user(user_or_username)
        pipeline = MongoQueries.enrollment_get_enrolled_projects(user, include_inactive)
        return [_project.Project(**i) for i in self.collection.aggregate(pipeline)]

    def get_enrolled_projects_raw(
        self, user_or_username: "str | _user.User", include_inactive: bool = False
    ) -> list[RawEnrolledProjectsDict]:
        """Return list of projects that a user has enrolled to.

        The output of the function is in raw format
        :param username: User username.
        :type username: str
        :param include_inactive: Search for enrollments that are not active as well.
            Defaults to False.
        :type include_inactive: bool
        :raises UserNotExistsException: Given user could not be found in the database.
        :return: A list of enrolled projects for the given user.
        :rtype: list[RawEnrolledProjectsDict]
        """
        user = self._get_user(user_or_username)
        pipeline = MongoQueries.enrollment_get_enrolled_projects_raw(user, include_inactive)
        return [i for i in self.collection.aggregate(pipeline)]

    def get_all_enrolled_projects_raw(self, user_or_username: "str | _user.User") -> list[dict]:
        """Return list of projects that a user has enrolled to in raw format.

        The output of the function is in raw format
        :param user_or_username: User instance or username.
        :type user_or_username: str | _user.User
        :raises UserNotExistsException: Given user could not be found in the database.
        :return: A list of enrolled projects for the given user.
        :rtype: list[RawEnrolledProjectsDict]
        """
        user = self._get_user(user_or_username)
        pipeline = MongoQueries.enrollment_get_all_enrolled_projects(user)
        return [i for i in self.collection.aggregate(pipeline)]

    # GET LEADERBOARD
    def get_leaderboard(self, project: "_project.Project") -> list[LeaderBoardItem]:
        """Calculate leaderboard data using MongoDB aggregation pipeline.

        :param project: A selected project.
        :type project: _project.Project
        :return: A list of tranformed leaderboard objects.
        :rtype: list[LeaderBoardItem]
        """

        try:
            project_cluster = self._project_cluster_mgr.get_cluster(project)
        except ProjectClusterNotExistException:
            project_cluster = None

        def _transform_items(items) -> list[LeaderBoardItem]:
            """Transform fetch data to final format."""
            out: list[LeaderBoardItem] = []
            for obj in items:
                eid = obj["_id"]
                user_cluster = self._user_cluster_mgr.get_doc_by_filter(
                    **{"enrollment_id.$id": eid}
                )
                total = count_submittable_secret_slots(user_cluster, project_cluster)
                solved = obj["progress"].get("solved_secrets") or {}
                out.append(
                    {
                        "secrets": solved,
                        "found_secrets": obj["progress"]["found_secrets"],
                        "last_submit_time": obj["progress"]["last_submit_time"],
                        "total_secrets": total,
                        "user": obj["user"],
                    }
                )
            return out

        pipeline = MongoQueries.enrollment_fetch_leaderboard(project)
        fetch_leaderboard_items = list(self.collection.aggregate(pipeline))
        return _transform_items(fetch_leaderboard_items)

    # CANCEL USER ENROLLMENTS

    async def disable_enrollment(
        self,
        user_or_username: "str | _user.User",
        project_or_name: "str | _project.Project",
    ):
        """Set an enrollment document to inactive.

        Stops all the clusters and set the object to `active=False`.

        :param project_or_name: Project name or the instance.
        :type project_or_name: str | Project
        :param user_or_username: User instance or username.
        :type user_or_username: str | _user.User
        :raises UserNotEnrolledToProjectException: When user is not enrolled to the project.
        """
        user, project = self._get_user_and_project(user_or_username, project_or_name)

        enrollment = self.get_doc_by_filter(
            **{
                "user_id.$id": user.id,
                "project_id.$id": project.id,
                "active": True,
            }
        )

        if not enrollment:
            raise UserNotEnrolledToProjectException(
                f"User `{user.username}` is not enrolled to the project `{project.name}`"
            )

        cluster = self._user_cluster_mgr.get_cluster(enrollment)
        await self._user_cluster_mgr.stop_cluster(cluster, self)

        enrollment.active = False
        self.update_doc(enrollment)

    async def disable_multiple_enrollments(
        self, user_project_pairs: list[tuple["_user.User", "_project.Project"]]
    ):
        """Set multiple enrollment documents inactive.

        Stops all the clusters and set the object to `active=False`.

        :param user_project_pairs: A list of pairs user-project.
        :type user_project_pairs: list[tuple[_user.User, _project.Project]]
        """
        if not user_project_pairs:
            return

        enroll_ids = []

        for user, project in user_project_pairs:
            enrollment = self.get_doc_by_filter(
                **{"user_id.$id": user.id, "project_id.$id": project.id, "active": True}
            )
            if enrollment:
                # Find cluster for this enrollment
                cluster = self._user_cluster_mgr.get_doc_by_filter(
                    **{"enrollment_id.$id": enrollment.id}
                )
                if cluster:
                    # clusters_to_delete.append(cluster)
                    await self._user_cluster_mgr.stop_cluster(cluster, self)

                enroll_ids.append(enrollment.id)

        # Mark enrollments as inactive
        self.collection.update_many({"_id": {"$in": enroll_ids}}, {"$set": {"active": False}})

    async def flush_enrollment(
        self,
        user_or_username: "str | _user.User",
        project_or_name: "str | _project.Project",
    ):
        """Completely remove data related to the enrollment from the host machine.

        Only works if the document is not active.

        :param project_or_name: Project name or the instance.
        :type project_or_name: str | Project
        :param user_or_username: User instance or username.
        :type user_or_username: str | _user.User
        :raises UserExistsException: When the user document is still active.
        """
        try:
            user = self._repo.get_user(user_or_username, None)
            project = self._repo.get_project(project_or_name, None)
        except (UserNotExistsException, ProjectNotExistException):
            return

        enrollment = self.get_doc_by_filter(
            **{
                "user_id.$id": user.id,
                "project_id.$id": project.id,
            }
        )

        if not enrollment:
            return
        if enrollment.active:
            raise UserEnrolledToProjectException("Cannot flush data when the enrollment is active.")

        # Get and delete cluster (this will clean up scenarios)
        cluster = self._user_cluster_mgr.get_cluster(enrollment)
        n_map = self._user_cluster_mgr.get_network_map(cluster)
        self.c_client.rm_network(project.name, n_map["private"])

        await self._user_cluster_mgr.delete_cluster(cluster, self)

        # Remove enrollment directory (should be empty after cluster deletion)
        enrolled_user_path = self.paths.enrolled_user_path(user, project)
        if enrolled_user_path.exists():
            shutil.rmtree(enrolled_user_path)

        self.remove_doc_by_id(enrollment.id)

    async def flush_multiple_enrollments(
        self, user_project_pairs: list[tuple["_user.User", "_project.Project"]]
    ):
        """Removes data related to the enrollments from the host machine.

        Only inactive enrollment documents will proceed for the removal operations.

        :param user_project_pairs: A list of pairs user-project.
        :type user_project_pairs: list[tuple[_user.User, _project.Project]]
        """
        if not user_project_pairs:
            return
        pipeline = MongoQueries.enrollment_aggregate_pairs_user_project(user_project_pairs)
        query_res = [i for i in self.collection.aggregate(pipeline)]
        for data in query_res:
            user = _user.User(**data["user"])
            project = _project.Project(**data["project"])
            await self.flush_enrollment(user, project)

        self.remove_docs_by_id([data["_id"] for data in query_res])

    async def cancel_enrollment(
        self,
        user_or_username: "str | _user.User",
        project_or_name: "str | _project.Project",
    ):
        """Cancel enrollment.

        :param user_or_username: User username or user object.
        :type user_or_username: str | _user.User
        :param project_or_name: Project name or project object.
        :type project_or_name: str | _project.Project
        :raises UserNotExistsException: User with the given username was not found.
        :raises ProjectNotExistException: Project data was not found in the database.
        :raises UserNotEnrolledToProjectException: User is not enrolled to the given
        project.
        """
        await self.disable_enrollment(user_or_username, project_or_name)
        await self.flush_enrollment(user_or_username, project_or_name)

    async def cancel_multiple_enrollments(
        self,
        lof_usernames: list[str],
        project_or_name: "str | _project.Project",
        user_mgr: "_user.UserManager",
    ):
        """Cancel multiple enrollment to a selected project.

        :param lof_usernames: A list of usernames.
        :type lof_usernames: list[str]
        :param project_or_name: Project name or project object.
        :type project_or_name: str | _project.Project
        :param user_mgr: User manager
        :type user_mgr: UserManager
        :raises ProjectNotExistException: Project data was not found in the database.
        """
        project = self._repo.get_project(project_or_name, None)
        pairs_user_project = [
            (user, project) for user in user_mgr.get_docs(username={"$in": lof_usernames})
        ]
        await self.disable_multiple_enrollments(pairs_user_project)
        await self.flush_multiple_enrollments(pairs_user_project)

    async def cancel_all_project_enrollments(self, project_or_name: "str | _project.Project"):
        """Remove all enrollments for the given project.

        :param project_or_name: Project name or `Project` object.
        :type project_or_name: str | _project.Project
        :raises ProjectNotExistException: Project data was not found in the database.
        """
        project = self._repo.get_project(project_or_name, None)
        pairs_user_project = [(user, project) for user in self.get_enrollments_for_project(project)]
        await self.disable_multiple_enrollments(pairs_user_project)
        await self.flush_multiple_enrollments(pairs_user_project)

    async def cancel_user_from_all_projects(self, user_or_username: "str | _user.User"):
        """Remove user from all enrolled projects.

        :param user_or_username: User username or `User` object.
        :type user_or_username: str | _user.User
        :raises UserNotExistsException: User with the given username was not found.
        """

        user = self._get_user(user_or_username)
        pairs_user_project = [(user, project) for project in self.get_enrolled_projects(user)]
        await self.disable_multiple_enrollments(pairs_user_project)
        await self.flush_multiple_enrollments(pairs_user_project)

    async def delete_all(self, prj_mgr: "_project.ProjectManager"):
        """Remove all canceled enrollments.

        :param prj_mgr: Project manager.
        :type prj_mgr: ProjectManager
        """
        for prj in prj_mgr.get_docs():
            await self.cancel_all_project_enrollments(prj)

    def submit_secret(self, enrollment: Enrollment, value: str, prj_mgr: "_project.ProjectManager"):
        return super()._submit_secret(enrollment, value, prj_mgr, self)

    def record_session(
        self, enrollment: Enrollment, state: ProgressSession.State, info: dict[str, Any] = {}
    ):
        return super()._record_session(enrollment, state, self, info)
