import pathlib
from shutil import copytree, rmtree

import fit_ctf.ctf_base as ctf_base
from fit_ctf.path_mgmt import PathManagement
import fit_ctf_models.project as prj
import fit_ctf_models.user_enrollment as user_enroll
from fit_ctf_components.base import BaseComponent
from fit_ctf_components.container_client.container_client_interface import (
    ContainerClientInterface,
)
from fit_ctf_models.utils.exceptions import (
    ModuleExistsException,
    ModuleInUseException,
    ModuleNotExistsException,
)
from fit_ctf_templates import TEMPLATE_DIRNAME


class ModuleManager(BaseComponent):

    def __init__(
        self,
        ctf_base: "ctf_base.CTFBase",
    ):
        super().__init__(ctf_base)

    @property
    def prj_mgr(self) -> "prj.ProjectManager":
        return self.ctf_base.prj_mgr

    @property
    def ue_mgr(self) -> "user_enroll.UserEnrollmentManager":
        return self.ctf_base.ue_mgr

    @property
    def c_client(self) -> ContainerClientInterface:
        return self.ctf_base.c_client

    @property
    def paths(self) -> PathManagement:
        return self.ctf_base.paths

    def create_module(self, module_name: str):
        """Create a template module.

        :param module_name: A name of the module.
        :type module_name: str
        """
        dst_path = self.paths.module_global / module_name
        if dst_path.is_dir():
            raise ModuleExistsException(f"Module `{module_name}` already exists.")

        src_path = pathlib.Path(TEMPLATE_DIRNAME) / "v1" / "modules"
        copytree(src_path, dst_path)

    def list_modules(self) -> dict[str, pathlib.Path]:
        """Get a listing of modules on the host."""
        out = {}
        for path in self.paths.module_global.iterdir():
            if path.is_dir():
                out[path.name] = path.resolve()
        return out

    def get_path(self, module_name: str) -> pathlib.Path:
        """Get path to the module."""
        dir_path = self.paths.module_global / module_name
        if not dir_path.is_dir():
            raise ModuleNotExistsException(
                f"Cannot locate a path to module `{module_name}`."
            )
        return dir_path

    def reference_count(self, project_name: str | None) -> dict[str, int]:
        """Get the number of occurences of each active module in services."""
        module_count = {
            item["_id"]: item["count"]
            for item in self.ue_mgr.get_modules_count(project_name)
        }
        for mc in self.prj_mgr.get_modules_count(project_name):
            module_count.setdefault(mc["_id"], 0)
            module_count[mc["_id"]] += mc["count"]
        return module_count

    async def remove_module(self, module_name: str):
        """Remove module from the host."""
        module_path = self.get_path(module_name)
        module_count = self.reference_count(None)
        if module_count.get(module_name, 0) > 0:
            raise ModuleInUseException(
                f"Module `{module_name}` is still used by some services."
            )
        await self.c_client.rm_images(__name__, module_name, True)
        rmtree(module_path)
