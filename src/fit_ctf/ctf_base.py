from typing import TYPE_CHECKING

import pymongo
from pymongo.database import Database

import fit_ctf.components.container_client.container_client_interface as c_client_interface
from fit_ctf.path_mgmt import PathManagement
from fit_ctf.components.logger.default_logger import DefaultLogger
from fit_ctf.components.logger.logger_interface import LoggerInterface
from fit_ctf.components.types import EnvInfo, PathDict

if TYPE_CHECKING:
    import fit_ctf.models.infra as clusters
    import fit_ctf.models.core.enrollment as enroll
    import fit_ctf.models.core.module_manager as module_manager
    import fit_ctf.models.core.project as prj
    import fit_ctf.models.core.user as user


class CTFBase:
    def __init__(
        self,
        env_info: EnvInfo,
        paths: PathDict,
        mongo_client: pymongo.MongoClient,
        _c_client: type["c_client_interface.ContainerClientInterface"],
        logger_cls: type[LoggerInterface] = DefaultLogger,
    ) -> None:
        self._env_info = env_info
        self._mongo_client = mongo_client
        self._ctf_db: Database | None = None
        self._path_mgmt = PathManagement(paths)
        self._logger = logger_cls(self)
        self._c_client = _c_client(self)

        # Initialize managers eagerly to avoid circular dependency issues
        self._init_managers()

    def _init_managers(self):
        """Initialize all managers in linear order (no circular dependencies)."""
        from fit_ctf.models.core.project import Project, ProjectManager
        from fit_ctf.models.core.user import User, UserManager
        from fit_ctf.models.core.enrollment import Enrollment, EnrollmentManager
        from fit_ctf.models.core.module_manager import ModuleManager
        from fit_ctf.models.core.repository import EntityRepository
        from fit_ctf.models.infra import (
            UserCluster,
            UserClusterManager,
            ProjectCluster,
            ProjectClusterManager,
            ScenarioManager,
        )

        # Create shared repository first
        self._repo = EntityRepository(db=self.ctf_db)

        # Leaf managers (no manager dependencies)
        self._scenario_mgr: "clusters.ScenarioManager" = ScenarioManager(
            paths=self._path_mgmt
        )

        self._module_mgr: "module_manager.ModuleManager" = ModuleManager(
            c_client=self._c_client,
            paths=self._path_mgmt,
        )

        self._project_cluster_mgr: "clusters.ProjectClusterManager" = (
            ProjectClusterManager(
                db=self.ctf_db,
                coll=self.ctf_db["project_cluster"],
                model_cls=ProjectCluster,
                repo=self._repo,
                c_client=self._c_client,
                paths=self._path_mgmt,
                logger=self._logger,
            )
        )

        # Mid-level managers
        self._user_cluster_mgr: "clusters.UserClusterManager" = UserClusterManager(
            db=self.ctf_db,
            coll=self.ctf_db["user_cluster"],
            model_cls=UserCluster,
            repo=self._repo,
            project_cluster_mgr=self._project_cluster_mgr,
            c_client=self._c_client,
            paths=self._path_mgmt,
            logger=self._logger,
        )

        self._prj_mgr: "prj.ProjectManager" = ProjectManager(
            db=self.ctf_db,
            coll=self.ctf_db["project"],
            model_cls=Project,
            repo=self._repo,
            project_cluster_mgr=self._project_cluster_mgr,
            user_cluster_mgr=self._user_cluster_mgr,
            c_client=self._c_client,
            paths=self._path_mgmt,
            logger=self._logger,
        )

        self._user_mgr: "user.UserManager" = UserManager(
            db=self.ctf_db,
            coll=self.ctf_db["user"],
            model_cls=User,
            repo=self._repo,
            user_cluster_mgr=self._user_cluster_mgr,
            c_client=self._c_client,
            paths=self._path_mgmt,
            logger=self._logger,
        )

        # Top-level manager
        self._enroll_mgr: "enroll.EnrollmentManager" = EnrollmentManager(
            db=self.ctf_db,
            coll=self.ctf_db["enrollment"],
            model_cls=Enrollment,
            repo=self._repo,
            user_cluster_mgr=self._user_cluster_mgr,
            project_cluster_mgr=self._project_cluster_mgr,
            c_client=self._c_client,
            paths=self._path_mgmt,
            logger=self._logger,
        )

        # NO two-phase wiring - clean linear initialization!

    @property
    def mongo_client(self) -> pymongo.MongoClient:
        return self._mongo_client

    @property
    def ctf_db(self) -> Database:
        if self._ctf_db is None:
            self._ctf_db = self.mongo_client[self._env_info["db_name"]]
        return self._ctf_db

    @property
    def prj_mgr(self) -> "prj.ProjectManager":
        """Returns a project manager.

        :return: A project manager initialized in CTFApp.
        :rtype: ProjectManager
        """
        return self._prj_mgr

    @property
    def user_mgr(self) -> "user.UserManager":
        """Returns a user manager.

        :return: A user manager initialized in CTFApp.
        :rtype: UserManager
        """
        return self._user_mgr

    @property
    def enroll_mgr(self) -> "enroll.EnrollmentManager":
        """Returns an enrollment manager.

        :return: An enrollment manager initialized in CTFApp.
        :rtype: EnrollmentManager
        """
        return self._enroll_mgr

    @property
    def module_mgr(self) -> "module_manager.ModuleManager":
        """Returns a module manager.

        :return: A module manager initialized in CTFApp.
        :rtype: ModuleManager
        """
        return self._module_mgr

    @property
    def user_cluster_mgr(self) -> "clusters.UserClusterManager":
        return self._user_cluster_mgr

    @property
    def project_cluster_mgr(self) -> "clusters.ProjectClusterManager":
        return self._project_cluster_mgr

    @property
    def scenario_mgr(self) -> "clusters.ScenarioManager":
        return self._scenario_mgr

    @property
    def c_client(self) -> "c_client_interface.ContainerClientInterface":
        return self._c_client

    @property
    def logger(self) -> LoggerInterface:
        return self._logger

    @property
    def paths(self) -> PathManagement:
        return self._path_mgmt
