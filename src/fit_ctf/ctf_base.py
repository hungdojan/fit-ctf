import os
from typing import TYPE_CHECKING, overload

import pymongo
from pymongo.database import Database

import fit_ctf_components.container_client.container_client_interface as c_client_interface
from fit_ctf.exceptions import ManagerNotFound
from fit_ctf.path_mgmt import PathManagement
from fit_ctf_components.base import BaseComponent, ComponentType
from fit_ctf_components.logger.default_logger import DefaultLogger
from fit_ctf_components.logger.logger_interface import LoggerInterface
from fit_ctf_components.types import EnvInfo, PathDict

if TYPE_CHECKING:
    import fit_ctf_models.clusters as clusters
    import fit_ctf_models.enrollment as enroll
    import fit_ctf_models.module_manager as module_manager
    import fit_ctf_models.project as prj
    import fit_ctf_models.user as user


class CTFBase:
    def __init__(
        self,
        env_info: EnvInfo,
        paths: PathDict,
        _c_client: type["c_client_interface.ContainerClientInterface"],
        logger_cls: type[LoggerInterface] = DefaultLogger,
    ) -> None:
        self._env_info = env_info
        self._db_uri = (
            f"mongodb://{env_info['db_username']}:"
            f"{env_info['db_password']}@{env_info['db_host']}:{env_info['db_port']}/"
        )
        if env_info["db_name"]:
            self._db_uri += f"{env_info['db_name']}"
        # FIX: remove hardcoded parameter
        self._db_uri += "?authSource=admin"

        self._mongo_client: pymongo.MongoClient | None = None
        self._ctf_db: Database | None = None
        self._c_client = _c_client(self)
        self._managers = {}
        self._path_mgmt = PathManagement(paths)
        self._components: dict[str, BaseComponent] = {
            "logger": logger_cls(self),
        }

    @property
    def mongo_client(self) -> pymongo.MongoClient:
        if not self._mongo_client:
            self._mongo_client = pymongo.MongoClient(
                self._db_uri,
                serverSelectionTimeoutMS=int(os.getenv("DB_CONNECTION_TIMEOUT", "30")),
                tz_aware=True,
            )
            self._mongo_client.server_info()
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
        from fit_ctf_models.project import ProjectManager

        if self._managers.get("project", None) is None:
            self._managers["project"] = ProjectManager(self, self.ctf_db)
        return self._managers["project"]

    @property
    def user_mgr(self) -> "user.UserManager":
        """Returns a user manager.

        :return: A user manager initialized in CTFApp.
        :rtype: UserManager
        """
        from fit_ctf_models.user import UserManager

        if self._managers.get("user", None) is None:
            self._managers["user"] = UserManager(self, self.ctf_db)
        return self._managers["user"]

    @property
    def enroll_mgr(self) -> "enroll.EnrollmentManager":
        """Returns an enrollment manager.

        :return: An enrollment manager initialized in CTFApp.
        :rtype: EnrollmentManager
        """
        from fit_ctf_models.enrollment import EnrollmentManager

        if self._managers.get("enrollment", None) is None:
            self._managers["enrollment"] = EnrollmentManager(self, self.ctf_db)
        return self._managers["enrollment"]

    @property
    def module_mgr(self) -> "module_manager.ModuleManager":
        """Returns an enrollment manager.

        :return: An enrollment manager initialized in CTFApp.
        :rtype: EnrollmentManager
        """
        from fit_ctf_models.module_manager import ModuleManager

        if self._managers.get("module", None) is None:
            self._managers["module"] = ModuleManager(self)
        return self._managers["module"]

    @property
    def user_cluster_mgr(self) -> "clusters.UserClusterManager":
        from fit_ctf_models.clusters import UserClusterManager

        if self._managers.get("user_cluster", None) is None:
            self._managers["user_cluster"] = UserClusterManager(self, self.ctf_db)
        return self._managers["user_cluster"]

    @property
    def project_cluster_mgr(self) -> "clusters.ProjectClusterManager":
        from fit_ctf_models.clusters import ProjectClusterManager

        if self._managers.get("project_cluster", None) is None:
            self._managers["project_cluster"] = ProjectClusterManager(self, self.ctf_db)
        return self._managers["project_cluster"]

    @property
    def scenario_mgr(self) -> "clusters.ScenarioManager":
        from fit_ctf_models.clusters import ScenarioManager

        if self._managers.get("scenario", None) is None:
            self._managers["scenario"] = ScenarioManager(self)
        return self._managers["scenario"]

    @property
    def c_client(self) -> "c_client_interface.ContainerClientInterface":
        return self._c_client

    @property
    def logger(self) -> LoggerInterface:
        return self.get_component("logger", LoggerInterface)

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
