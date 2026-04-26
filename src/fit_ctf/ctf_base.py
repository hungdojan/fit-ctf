from typing import TYPE_CHECKING, overload

import pymongo
from pymongo.database import Database

import fit_ctf.components.container_client.container_client_interface as c_client_interface
from fit_ctf.exceptions import ManagerNotFound
from fit_ctf.path_mgmt import PathManagement
from fit_ctf.components.base import BaseComponent, ComponentType
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

        self._components: dict[str, BaseComponent] = {
            "logger": self._logger,
        }

    def _init_managers(self):
        """Initialize all managers in correct order to handle circular dependencies."""
        from fit_ctf.models.core.project import Project, ProjectManager
        from fit_ctf.models.core.user import User, UserManager
        from fit_ctf.models.core.enrollment import Enrollment, EnrollmentManager
        from fit_ctf.models.core.module_manager import ModuleManager
        from fit_ctf.models.infra import (
            UserCluster,
            UserClusterManager,
            ProjectCluster,
            ProjectClusterManager,
            ScenarioManager,
        )

        # Create project_cluster_mgr first (depends only on prj_mgr, will be set later)
        self._project_cluster_mgr: "clusters.ProjectClusterManager" = (
            ProjectClusterManager(
                db=self.ctf_db,
                coll=self.ctf_db["project_cluster"],
                model_cls=ProjectCluster,
                prj_mgr=None,  # Will be set after prj_mgr is created
                c_client=self._c_client,
                paths=self._path_mgmt,
                logger=self._logger,
            )
        )

        # Create user_cluster_mgr (depends on prj_mgr, enroll_mgr, project_cluster_mgr)
        self._user_cluster_mgr: "clusters.UserClusterManager" = UserClusterManager(
            db=self.ctf_db,
            coll=self.ctf_db["user_cluster"],
            model_cls=UserCluster,
            prj_mgr=None,  # Will be set later
            enroll_mgr=None,  # Will be set later
            project_cluster_mgr=self._project_cluster_mgr,
            c_client=self._c_client,
            paths=self._path_mgmt,
            logger=self._logger,
        )

        # Create enroll_mgr (depends on prj_mgr, user_mgr, cluster managers)
        self._enroll_mgr: "enroll.EnrollmentManager" = EnrollmentManager(
            db=self.ctf_db,
            coll=self.ctf_db["enrollment"],
            model_cls=Enrollment,
            prj_mgr=None,  # Will be set later
            user_mgr=None,  # Will be set later
            user_cluster_mgr=self._user_cluster_mgr,
            project_cluster_mgr=self._project_cluster_mgr,
            c_client=self._c_client,
            paths=self._path_mgmt,
            logger=self._logger,
        )

        # Create prj_mgr (depends on enroll_mgr, cluster managers)
        self._prj_mgr: "prj.ProjectManager" = ProjectManager(
            db=self.ctf_db,
            coll=self.ctf_db["project"],
            model_cls=Project,
            enroll_mgr=self._enroll_mgr,
            project_cluster_mgr=self._project_cluster_mgr,
            user_cluster_mgr=self._user_cluster_mgr,
            c_client=self._c_client,
            paths=self._path_mgmt,
            logger=self._logger,
        )

        # Create user_mgr (depends on enroll_mgr, user_cluster_mgr)
        self._user_mgr: "user.UserManager" = UserManager(
            db=self.ctf_db,
            coll=self.ctf_db["user"],
            model_cls=User,
            enroll_mgr=self._enroll_mgr,
            user_cluster_mgr=self._user_cluster_mgr,
            c_client=self._c_client,
            paths=self._path_mgmt,
            logger=self._logger,
        )

        # Now fix circular dependencies by setting the managers that were None
        self._project_cluster_mgr._prj_mgr = self._prj_mgr
        self._user_cluster_mgr._prj_mgr = self._prj_mgr
        self._user_cluster_mgr._enroll_mgr = self._enroll_mgr
        self._enroll_mgr._prj_mgr = self._prj_mgr
        self._enroll_mgr._user_mgr = self._user_mgr

        # Create module_mgr (depends on prj_mgr, enroll_mgr)
        self._module_mgr: "module_manager.ModuleManager" = ModuleManager(
            prj_mgr=self._prj_mgr,
            enroll_mgr=self._enroll_mgr,
            c_client=self._c_client,
            paths=self._path_mgmt,
        )

        # Create scenario_mgr (depends on user_cluster_mgr, enroll_mgr)
        self._scenario_mgr: "clusters.ScenarioManager" = ScenarioManager(
            paths=self._path_mgmt,
            user_cluster_mgr=self._user_cluster_mgr,
            enroll_mgr=self._enroll_mgr,
        )

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

    @overload
    def get_component(self, name: str) -> BaseComponent: ...

    @overload
    def get_component(self, name: str, _type: type[ComponentType]) -> ComponentType: ...

    def get_component(
        self, name: str, _type: type[ComponentType] | None = None
    ) -> ComponentType | BaseComponent:
        mgr = self._components.get(name)
        if not mgr:
            raise ManagerNotFound(f"Manager {name} was not found.")
        if _type is not None:
            # wrong type
            if not isinstance(mgr, _type):
                raise ManagerNotFound(f"Manager {name} was not found.")
        return mgr

    def register_component(self, name: str, component: BaseComponent):
        self._components[name] = component
