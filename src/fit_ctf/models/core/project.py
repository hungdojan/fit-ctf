import os
import re
import shutil
from typing import TYPE_CHECKING

from pymongo.database import Database

from fit_ctf.exceptions import CTFBaseException
import fit_ctf.models.infra.project_cluster as prj_cluster
from fit_ctf.components.constants import DEFAULT_STARTING_PORT
from fit_ctf.components.types import (
    ProjectPortListingDict,
    RawProjectDict,
)
from fit_ctf.models.core.base import Base, BaseManagerInterface
from fit_ctf.models.utils.exceptions import (
    ProjectExistsException,
    ProjectNamingFormatException,
    ProjectNotExistException,
    SSHPortOutOfRangeException,
)
from fit_ctf.models.utils.mongo_queries import MongoQueries

if TYPE_CHECKING:
    import fit_ctf.ctf_base as ctf_base
    import fit_ctf.models.core.enrollment as enroll


class Project(Base):
    """A class that represents a project.

    :param name: Project's name.
    :type name: str
    :param config_root_dir: A directory containing all project configuration files.
    :type name: str
    :param volume_mount_dir: A path to a directory containing user volume objects.
    :type volume_mount_dir: str
    :param max_nof_users: Number of users that can enroll the project.
    :type max_nof_users: int
    :param starting_port_bind: A ssh port of the first enrolled user
    :type starting_port_bind: int
    :param description: A project description.
    :type description: str
    :param project_modules: List of project modules. Defaults to [].
    :type project_modules: dict[str, Module], optional
    :param user_modules: List of user modules. Defaults to [].
    :type user_modules: dict[str, Module], optional
    """

    name: str
    max_nof_users: int
    starting_port_bind: int
    description: str = ""

    @property
    def max_port(self) -> int:
        return self.starting_port_bind + self.max_nof_users - 1


class ProjectManager(BaseManagerInterface[Project]):
    """A manager class that handles operations with `Project` objects."""

    def __init__(
        self,
        ctf_base: "ctf_base.CTFBase",
        db: Database,
    ):
        """Constructor method.

        :param db: A MongoDB database object.
        :type db: Database
        :param paths: A list of content paths.
        :type paths: PathDict
        """
        super().__init__(ctf_base, db, db["project"], Project)

    @property
    def enroll_mgr(self) -> "enroll.EnrollmentManager":
        """Returns an enrollment manager.

        :return: An enrollment manager initialized in ProjectManager.
        :rtype: _enroll.EnrollmentManager
        """
        return self.ctf_base.enroll_mgr

    @property
    def project_cluster_mgr(self) -> "prj_cluster.ProjectClusterManager":
        """Returns project cluster manager.

        :return: Project cluster manager from CTF base.
        :rtype: ProjectClusterManager
        """
        return self.ctf_base.project_cluster_mgr

    def get_project(
        self, project_or_name: str | Project, active: bool | None = True
    ) -> Project:
        """Retrieve project data from the database.

        If the given argument is a Project instance, it will simple return
        the argument.

        :param project_or_name: Project name or the instance.
        :type name: str | Project
        :param active: Fetch documents with the given active value. If set to None,
            the function fetches both active and inactive documents. Defaults to True.
        :type active: bool | None
        :raises ProjectNotExistException: Project data was not found in the database.
        :return: The retrieved project object.
        :rtype: Project
        """
        if isinstance(project_or_name, Project):
            return project_or_name
        name = project_or_name
        _filter: dict = {"name": name}
        if active is not None:
            _filter["active"] = active
        prj = self.get_doc_by_filter(**_filter)
        if not prj:
            raise ProjectNotExistException(f"Project `{name}` does not exist.")
        return prj

    # def get_compose_files(self, project: Project) -> Path:
    #     """Return a path to the project's compose file.
    #
    #     If the file does not exist it will be compiled.
    #
    #     :param project: The project in question.
    #     :type project: Project
    #     :return: A path to the compose file.
    #     :rtype: Path
    #     """
    #     compose_file = self.paths.project_compose(project)
    #     if not compose_file.exists():
    #         self.compile_compose_file(project)
    #     return compose_file

    def _get_available_starting_port(self) -> int:
        """A function that calculates an available starting SSH port.

        :return: A vacant port.
        :rtype: int
        """
        # get sorted list of starting ports of all projects
        lof_prjs_cur = self._coll.find(
            filter={"active": True},
            projection={"_id": 0, "max_nof_users": 1, "starting_port_bind": 1},
        ).sort({"starting_port_bind": -1})
        lof_prjs = [i for i in lof_prjs_cur]

        if not lof_prjs:
            return DEFAULT_STARTING_PORT

        return lof_prjs[0]["starting_port_bind"] + lof_prjs[0]["max_nof_users"]

    def get_reserved_ports(self) -> list[ProjectPortListingDict]:
        """Get a list of reserved ports.

        :return: A list of reserved port ranges.
        :rtype: list[ProjectPortListingDict]
        """
        pipeline = MongoQueries.project_get_reserved_ports()
        return [i for i in self._coll.aggregate(pipeline)]

    @staticmethod
    def validate_project_name(project_name: str) -> bool:
        """Validate the project name format.

        The username can only contain lowercase characters, underscore, or digits.

        :param username: A username to validate.
        :type username: str
        :return: `True` if given project name meets all the criteria.
        :rtype: bool
        """
        return re.search(r"^[a-z0-9_]*$", project_name) is not None

    def init_project(
        self,
        name: str,
        max_nof_users: int,
        starting_port_bind: int = -1,
        description: str = "",
        **kw,
    ) -> Project:
        """Create a project from a template.

        :param name: Project's name. The support format for the name is `^[a-z0-9_]*$`.
            Uppercase or special characters are not allowed.
        :type name: str
        :param max_nof_users: Number of users that can enroll the project.
        :type max_nof_users: int
        :param starting_port_bind: A ssh port of the first enrolled user. When
            -1 is set the function will automatically find and assign available
            port. Defaults to -1.
        :type starting_port_bind: int, optional
        :param description: A project description. Defaults to "".
        :type description: str, optional

        :raises ProjectNamingFormatException: Project name does not follow the naming
            convention.
        :raises ProjectExistsException: Project with the given name already exist.
        :raises SSHPortOutOfRangeException: The ports that would be used in the project
            are outside the allowed range 1-65 535.
        :return: A created project object.
        :rtype: class `Project`
        """
        if not self.validate_project_name(name):
            raise ProjectNamingFormatException(
                f"Given name `{name}` is not allowed. "
                "Only lowercase characters, underscore and numbers are allowed."
            )
        # check if project already exists
        prj = self.get_doc_by_filter(name=name, active=True)
        if prj:
            raise ProjectExistsException(f"Project `{name}` already exists.")

        if starting_port_bind < 0:
            starting_port_bind = self._get_available_starting_port()

        if starting_port_bind == 0 or starting_port_bind + max_nof_users > 65_535:
            raise SSHPortOutOfRangeException(
                "Not enough available ports."
            )  # pragma: no cover

        self.paths.project_path(name).mkdir(parents=True)
        self.paths.project_users(name).mkdir(parents=True)
        self.paths.project_logs(name).mkdir(parents=True)

        prj = self.create_and_insert_doc(
            name=name,
            max_nof_users=max_nof_users,
            starting_port_bind=starting_port_bind,
            description=description,
        )

        self.project_cluster_mgr.create_cluster(
            prj_cluster.ProjectCluster.Builder(prj.name, prj).build()
        )
        n_map = self.project_cluster_mgr.get_network_map(prj)
        for n_name in n_map.values():
            self.c_client.create_networks(prj.name, [str(n_name)])

        return prj

    def generate_port_forwarding_script(
        self, project_or_name: str | Project, dest_ip_addr: str, filename: str
    ):
        """Generate a port forwarding script.

        :param project_or_name: Project name or the instance.
        :type project_or_name: str | Project
        :param dest_ip_addr: IP address of the destination machine/server.
        :type dest_ip_addr: str
        :param filename: And output filename.
        :type filename: str
        :raises ProjectNotExistException: Project data were not found in the database.
        """
        prj = self.get_project(project_or_name)

        lof_user_enrolls = self.enroll_mgr.get_docs_raw(
            filter={"project_id.$id": prj.id, "active": True},
            projection={"_id": 0, "container_port": 1, "forwarded_port": 1},
        )

        lof_cmd = [
            "firewall-cmd --zone=public "
            "--add-forward-port="
            f"port={i['forwarded_port']}:"
            "proto=tcp:"
            f"toport={i['container_port']}:"
            f"toaddr={dest_ip_addr}\n"
            for i in lof_user_enrolls
        ]

        with open(filename, "w") as f:
            f.write("#!/usr/bin/env bash\n\n")
            f.writelines(lof_cmd)
            f.write("firewall-cmd --zone=public --add-masquerade\n")
        os.chmod(filename, 0o755)

    async def disable_project(self, project_or_name: str | Project):
        """Set a project object to inactive.

        Stops all the clusters and set the object to `active=False`.

        :param project_or_name: Project name or the instance.
        :type project_or_name: str | Project
        """
        prj = self.get_project(project_or_name)

        # Stop project cluster if exists
        try:
            cluster = self.project_cluster_mgr.get_cluster(prj)
            await self.project_cluster_mgr.stop_cluster(cluster)
            # Stop all user clusters
            await self.ctf_base.user_cluster_mgr.stop_all_user_clusters(prj)

        except CTFBaseException:  # pragma: no cover
            pass  # No cluster exists
        await self.enroll_mgr.disable_multiple_enrollments(
            [(user, prj) for user in self.enroll_mgr.get_enrollments_for_project(prj)]
        )

        prj.active = False
        self.update_doc(prj)

    async def flush_project(self, project_or_name: str | Project):
        """Removes the object document and all the associated files from the host machine.

        The project object must be inactive.

        :param project_or_name: Project name or the instance.
        :type project_or_name: str | Project
        :raises ProjectExistsException: When the project is still active.
        """
        prj = self.get_project(project_or_name, None)
        if prj.active:
            raise ProjectExistsException("Cannot flush files of an active project.")

        path = self.paths.project_path(prj)
        if path.exists():
            shutil.rmtree(path)

        await self.enroll_mgr.flush_multiple_enrollments(
            [
                (user, prj)
                for user in self.enroll_mgr.get_enrollments_for_project(prj, True)
            ]
        )
        await self.project_cluster_mgr.delete_cluster(
            self.project_cluster_mgr.get_cluster(prj)
        )
        self.remove_doc_by_id(prj.id)
        n_map = self.project_cluster_mgr.get_network_map(prj)
        for n_name in n_map.values():
            self.c_client.rm_network(prj.name, str(n_name))

    async def delete_project(self, project_or_name: str | Project):
        """Delete a project.

        :param project_or_name: Project name or the instance.
        :type project_or_name: str | Project
        """
        # also deletes everything
        try:
            prj = self.get_project(project_or_name)
        except ProjectNotExistException:
            # TODO: log that project does not exist
            return

        await self.disable_project(prj)
        await self.flush_project(prj)

    def get_projects_raw(self, include_inactive: bool = False) -> list[RawProjectDict]:
        """Get list of all projects.

        The final directory has the following format:
        {
            "name": <project_name>,
            "max_nof_users": <max_nof_users>,
            "active_users": <nof_active_users>,
            "active": <active_status>
        }

        :param include_inactive: When `True` is set, function will also return `inactive`
        projects, defaults to False.
        :type include_inactive: bool, optional
        :return: A list of found projects in raw format.
        :rtype: list[RawProjectDict]
        """
        pipeline = MongoQueries.project_get_projects_raw(include_inactive)
        return [i for i in self.collection.aggregate(pipeline)]

    async def delete_all(self):
        """Remove all projects from the host system and clear database."""
        projects = self.get_docs()
        for prj in projects:
            await self.delete_project(prj)
