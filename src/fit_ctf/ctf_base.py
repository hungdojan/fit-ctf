import os
from typing import overload

import pymongo
from pymongo.database import Database

import fit_ctf_components.container_client.container_client_interface as c_client_interface
import fit_ctf_models.module_manager as module_mgr
import fit_ctf_models.project as prj
import fit_ctf_models.user as user
import fit_ctf_models.user_enrollment as user_enroll
from fit_ctf.exceptions import ManagerNotFound
from fit_ctf.path_mgmt import PathManagement
from fit_ctf_components.base import BaseComponent, ComponentType
from fit_ctf_components.logger.default_logger import DefaultLogger
from fit_ctf_components.logger.logger_interface import LoggerInterface
from fit_ctf_components.types import EnvInfo, PathDict


class CTFBase:
    def __init__(
        self,
        env_info: EnvInfo,
        paths: PathDict,
        _c_client: type["c_client_interface.ContainerClientInterface"],
        logger_cls: type[LoggerInterface] = DefaultLogger,
    ) -> None:
        self._client = pymongo.MongoClient(
            env_info["db_host"],
            serverSelectionTimeoutMS=int(os.getenv("DB_CONNECTION_TIMEOUT", "30")),
            tz_aware=True,
        )
        # test connection
        self._client.server_info()

        self._ctf_db: Database = self._client[env_info["db_name"]]

        self._c_client = _c_client(self)
        self._managers = {
            "project": prj.ProjectManager(self, self._ctf_db),
            "user": user.UserManager(self, self._ctf_db),
            "user_enrollment": user_enroll.UserEnrollmentManager(self, self._ctf_db),
            "module": module_mgr.ModuleManager(self),
        }
        self._path_mgmt = PathManagement(paths)
        self._components: dict[str, BaseComponent] = {
            "logger": logger_cls(self),
        }

    @property
    def prj_mgr(self) -> "prj.ProjectManager":
        """Returns a project manager.

        :return: A project manager initialized in CTFApp.
        :rtype: ProjectManager
        """
        return self._managers["project"]

    @property
    def user_mgr(self) -> "user.UserManager":
        """Returns a user manager.

        :return: A user manager initialized in CTFApp.
        :rtype: UserManager
        """
        return self._managers["user"]

    @property
    def ue_mgr(self) -> "user_enroll.UserEnrollmentManager":
        """Returns a user enrollment manager.

        :return: A user enrollment manager initialized in CTFApp.
        :rtype: UserEnrollmentManager
        """
        return self._managers["user_enrollment"]

    @property
    def module_mgr(self) -> "module_mgr.ModuleManager":
        """Returns a user enrollment manager.

        :return: A user enrollment manager initialized in CTFApp.
        :rtype: UserEnrollmentManager
        """
        return self._managers["module"]

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
