from pathlib import Path

import fit_ctf_models.project as _prj
import fit_ctf_models.user as _user
from fit_ctf_components.types import PathDict


class PathManagement:
    def __init__(self, paths: PathDict):
        self._paths = paths

    @property
    def project_global(self) -> Path:
        return self._paths["projects"]

    @property
    def user_global(self) -> Path:
        return self._paths["users"]

    @property
    def module_global(self) -> Path:
        return self._paths["modules"]

    def project_path(self, project_or_name: "str | _prj.Project") -> Path:
        if isinstance(project_or_name, str):
            return self.project_global / project_or_name
        return self.project_global / project_or_name.name

    def project_compose(self, project: "_prj.Project") -> Path:
        return self.project_global / project.name / "server_compose.yaml"

    def project_users(self, project_or_name: "str | _prj.Project") -> Path:
        return self.project_path(project_or_name) / "users"

    def project_logs(self, project_or_name: "str | _prj.Project") -> Path:
        return self.project_path(project_or_name) / "logs"

    def user_path(self, user_or_username: "str | _user.User") -> Path:
        if isinstance(user_or_username, str):
            return self.user_global / user_or_username
        return self.user_global / user_or_username.username

    def enrolled_user_path(self, user: "_user.User", project: "_prj.Project") -> Path:
        return self.project_users(project) / user.username

    def enrolled_user_secrets(
        self, user: "_user.User", project: "_prj.Project"
    ) -> Path:
        return self.enrolled_user_path(user, project) / "secrets"
