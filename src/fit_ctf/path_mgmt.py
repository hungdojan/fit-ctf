from pathlib import Path
from typing import TYPE_CHECKING

from fit_ctf.components.types import PathDict

if TYPE_CHECKING:
    import fit_ctf.models.core.project as _prj
    import fit_ctf.models.core.user as _user


class PathManagement:
    def __init__(self, paths: PathDict):
        self._paths: PathDict = paths

    @property
    def project_global(self) -> Path:
        return self._paths["projects"]

    @property
    def user_global(self) -> Path:
        return self._paths["users"]

    @property
    def module_global(self) -> Path:
        return self._paths["modules"]

    @property
    def scenario_global(self) -> Path:
        return self._paths["scenarios"]

    @property
    def paths_dict(self) -> PathDict:
        return self._paths

    def project_path(self, project_or_name: "str | _prj.Project") -> Path:
        if isinstance(project_or_name, str):
            return self.project_global / project_or_name
        return self.project_global / project_or_name.name

    def project_users(self, project_or_name: "str | _prj.Project") -> Path:
        return self.project_path(project_or_name) / "users"

    def project_logs(self, project_or_name: "str | _prj.Project") -> Path:
        return self.project_path(project_or_name) / "logs"

    def project_scenarios(self, project_or_name: "str | _prj.Project") -> Path:
        return self.project_path(project_or_name) / "scenarios"

    def user_path(self, user_or_username: "str | _user.User") -> Path:
        if isinstance(user_or_username, str):
            return self.user_global / user_or_username
        return self.user_global / user_or_username.username

    def enrolled_user_path(self, user: "_user.User", project: "_prj.Project") -> Path:
        return self.project_users(project) / user.username

    # def enrolled_user_secrets(
    #     self, user: "_user.User", project: "_prj.Project"
    # ) -> Path:
    #     return self.enrolled_user_path(user, project) / "secrets"
