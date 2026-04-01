import pathlib
import re
from collections import defaultdict
from shutil import copytree, rmtree
from typing import TYPE_CHECKING

import yaml

from fit_ctf.path_mgmt import PathManagement
from fit_ctf_components.base import BaseComponent
from fit_ctf_components.container_client.container_client_interface import (
    ContainerClientInterface,
)
from fit_ctf_components.types import ErrorCode
from fit_ctf_models.utils import flatten
from fit_ctf_models.utils.exceptions import (
    ModuleExistsException,
    ModuleInUseException,
    ModuleNotExistsException,
)
from fit_ctf_templates import TEMPLATE_DIRNAME

if TYPE_CHECKING:
    import fit_ctf.ctf_base as ctf_base
    import fit_ctf_models.enrollment as enroll
    import fit_ctf_models.project as prj
    import fit_ctf_models.user as user


class ModuleManager(BaseComponent):

    def __init__(self, ctf_base: "ctf_base.CTFBase"):
        super().__init__(ctf_base)

    @property
    def prj_mgr(self) -> "prj.ProjectManager":
        return self.ctf_base.prj_mgr

    @property
    def enroll_mgr(self) -> "enroll.EnrollmentManager":
        return self.ctf_base.enroll_mgr

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

    async def build_module(
        self, module_name: str, to_stdout: bool = False
    ) -> ErrorCode:
        """Build a module's container image.

        :param module_name: Name of the module to build
        :type module_name: str
        :param to_stdout: Pipe build output to stdout
        :type to_stdout: bool
        :return: An exit code
        :rtype: ErrorCode
        """
        dir_path = self.get_path(module_name)
        image_name = f"fit_ctf_module_{module_name}"
        return await self.c_client.build_image(
            logger_name=__name__,
            context_path=dir_path,
            image_name=image_name,
            containerfile="Containerfile",
            to_stdout=to_stdout,
        )

    def reference_count(self, project_name: str | None, all_images: bool = False) -> dict[str, int]:
        """Count module directory usage from compiled ``scenario_compose.yaml`` files.

        Scans project-level scenarios under ``project_scenarios`` and per-user
        scenarios under ``project_users/<user>/``. A hit is counted when
        ``services.*.build.context`` resolves under ``module_global``; the key is
        the first path segment (module folder name).

        :param project_name: Limit to one project, or ``None`` for all projects.
        :param all_images: If True, also count ``services.*.image`` strings (keys
            are full image references, not module directory names — useful for
            reporting only; ``remove_module`` does not use this mode).
        """

        def _project_usage(prj: "prj.Project") -> dict[str, int]:
            module_acc = defaultdict(int)
            for s in self.paths.project_scenarios(prj).iterdir():
                if not s.is_dir() or not (s / "scenario_compose.yaml").exists():
                    continue
                for module_name, count in _fetch_modules(
                    s / "scenario_compose.yaml"
                ).items():
                    module_acc[module_name] += count
            return module_acc

        def _user_usage(user: "user.User", project: "prj.Project") -> dict[str, int]:
            module_acc = defaultdict(int)
            user_root = self.paths.enrolled_user_path(user, project)
            if not user_root.is_dir():
                return module_acc
            for s in user_root.iterdir():
                if not s.is_dir() or not (s / "scenario_compose.yaml").exists():
                    continue
                for module_name, count in _fetch_modules(
                    s / "scenario_compose.yaml"
                ).items():
                    module_acc[module_name] += count
            return module_acc

        def _fetch_modules(file_path: pathlib.Path) -> dict[str, int]:
            out = defaultdict(int)
            context_parser = re.compile(r"^services.[^.]*.build.context$")
            image_parser = re.compile(r"^services.[^.]*.image$")
            module_root = str(self.paths.module_global.resolve())

            try:
                raw = yaml.safe_load(file_path.read_text())
            except OSError:
                return out
            except yaml.YAMLError:
                return out
            if not isinstance(raw, dict):
                return out
            data = flatten(raw)
            for k, v in data.items():
                if not isinstance(v, str):
                    continue
                if context_parser.match(k) and v.startswith(module_root):
                    module_name = v.removeprefix(module_root).lstrip("/")
                    if module_name:
                        out[module_name] += 1
                elif all_images and image_parser.match(k):
                    out[v] += 1
            return out

        if project_name:
            prjs = [self.ctf_base.prj_mgr.get_project(project_name)]
        else:
            prjs = self.ctf_base.prj_mgr.get_docs()
        modules = defaultdict(int)
        for prj in prjs:
            if self.paths.project_scenarios(prj).exists():
                for k, v in _project_usage(prj).items():
                    modules[k] += v
            for user in self.enroll_mgr.get_enrollments_for_project(prj):
                for k, v in _user_usage(user, prj).items():
                    modules[k] += v

        return dict(modules)

    async def remove_module(self, module_name: str):
        """Remove module from the host."""
        module_path = self.get_path(module_name)
        module_count = self.reference_count(None)
        if module_count.get(module_name, 0) > 0:
            raise ModuleInUseException(
                f"Module `{module_name}` is still used by some services."
            )
        _ = await self.c_client.rm_images(__name__, module_name, True)
        rmtree(module_path)
