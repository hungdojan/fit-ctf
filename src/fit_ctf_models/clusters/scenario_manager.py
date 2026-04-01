"""Scenario management for CTF platform."""

import pathlib
import re
import shutil
from typing import TYPE_CHECKING

from fit_ctf_components.base import BaseComponent
from fit_ctf_models.utils.exceptions import (
    ScenarioExistException,
    ScenarioNotExistException,
)
from fit_ctf_models.utils.mongo_queries import MongoQueries
from fit_ctf_templates import TEMPLATE_PATH_MAP, get_jinja_variables, get_template

if TYPE_CHECKING:
    import fit_ctf.ctf_base
    import fit_ctf_models.project as project

# `volumes/*.template`: `{service}__volume_map__{volume}__{param}` (four segments).
_VOL_MAP_TPL_PARAM_RE = re.compile(r"^(.+?)__volume_map__(.+?)__(.+)$")
# `{service}__port_map__`, `__env_map__`, `__volume_map__{volume}` (three segments).
_SC_TRIPLE_RE = re.compile(r"^(.*)__(.*)__(.*)$")


class ScenarioManager(BaseComponent):
    """Manager for CTF scenario templates and configurations."""

    def __init__(self, ctf_base: "fit_ctf.ctf_base.CTFBase"):
        """Initialize ScenarioManager.

        :param ctf_base: CTF base instance
        :type ctf_base: fit_ctf.ctf_base.CTFBase
        """
        super().__init__(ctf_base)

    @property
    def scenario_root(self) -> pathlib.Path:
        """Get root directory for scenario templates.

        :return: Path to scenario root directory
        :rtype: pathlib.Path
        """
        return self.ctf_base.paths.scenario_global

    @property
    def user_cluster_mgr(self):
        """Get user cluster manager instance.

        :return: UserClusterManager instance
        """
        return self.ctf_base.user_cluster_mgr

    def create_scenario(self, scenario_name: str):
        """Create a new scenario template.

        Creates directory structure and base template files for a new scenario.

        :param scenario_name: Name for the new scenario
        :type scenario_name: str
        :raises ScenarioExistException: If scenario already exists
        """
        # TODO: check security
        path = self.scenario_root / scenario_name
        if path.exists():
            raise ScenarioExistException(f"Scenario {scenario_name} already exists.")

        path.mkdir(parents=True)
        try:
            with open(path / "scenario_compose.yaml.j2", "w") as f:
                template = get_template("scenario_compose.yaml.j2")
                f.write(template.render(name=scenario_name))
            shutil.copytree(TEMPLATE_PATH_MAP["volumes"], path / "volumes")

        except Exception as e:
            # Clean up created directory if template creation fails
            if path.exists():
                shutil.rmtree(path)
            raise e

    def get_scenario_dir(self, scenario_name: str) -> pathlib.Path:
        """Get directory path for a scenario.

        :param scenario_name: Name of the scenario
        :type scenario_name: str
        :return: Path to scenario directory
        :rtype: pathlib.Path
        :raises ScenarioNotExistException: If scenario does not exist
        """
        path = self.scenario_root / scenario_name
        if not path.exists():
            raise ScenarioNotExistException(f"Scenario {scenario_name} does not exist")
        return path

    def fetch_variables(self, scenario_name: str) -> dict[str, str]:
        """Fetch Jinja2 template variables from scenario templates.

        Parses scenario compose templates and volume templates to extract
        required variables for configuration.

        :param scenario_name: Name of the scenario
        :type scenario_name: str
        :return: Dictionary of variables organized by service and type
        :rtype: dict[str, str]
        """
        scenario_dir = self.get_scenario_dir(scenario_name)
        vars_ = get_jinja_variables("scenario_compose.yaml.j2", scenario_dir)
        var_dict: dict = {}
        for v in vars_:
            m4 = _VOL_MAP_TPL_PARAM_RE.fullmatch(v)
            if m4:
                svc, vol, pkey = m4.group(1), m4.group(2), m4.group(3)
                var_dict.setdefault(svc, {}).setdefault("volume_map", {}).setdefault(
                    vol, {}
                ).setdefault("template_params", {})[pkey] = ""
                continue
            m = _SC_TRIPLE_RE.fullmatch(v)
            if m:
                svc, m_type, m_key = m.group(1), m.group(2), m.group(3)
                if m_type != "volume_map":
                    var_dict.setdefault(svc, {}).setdefault(m_type, {})[m_key] = ""
                else:
                    var_dict.setdefault(svc, {}).setdefault(m_type, {}).setdefault(
                        m_key, {}
                    )["src_path"] = ""

        if (scenario_dir / "volumes").exists():
            for file in (scenario_dir / "volumes").iterdir():
                if not file.name.endswith(".template"):
                    continue
                for v in get_jinja_variables(file.name, scenario_dir / "volumes"):
                    m4 = _VOL_MAP_TPL_PARAM_RE.fullmatch(v)
                    if m4:
                        var_dict.setdefault(m4.group(1), {}).setdefault(
                            "volume_map", {}
                        ).setdefault(m4.group(2), {}).setdefault("template_params", {})[
                            m4.group(3)
                        ] = ""

        return var_dict

    def list_scenarios(self) -> list[str]:
        """List all available scenario templates.

        :return: List of scenario names
        :rtype: list[str]
        """
        return [item.name for item in self.scenario_root.iterdir() if item.is_dir()]

    def scenario_usage_for_project(
        self, project: "project.Project", include_users: bool = False
    ) -> list[str]:
        def _fetch_scenarios(path: pathlib.Path) -> set[str]:
            if not path.exists():
                return set()
            return set(d.name for d in path.iterdir() if d.is_dir)

        usage = _fetch_scenarios(self.ctf_base.paths.project_scenarios(project))
        if include_users:
            enrolled_users = self.ctf_base.enroll_mgr.get_enrollments_for_project(
                project
            )
            for user in enrolled_users:
                usage.update(
                    _fetch_scenarios(
                        self.ctf_base.paths.enrolled_user_path(user, project)
                    )
                )
        return list(usage)

    def scenario_overview(self) -> dict[str, list[int]]:
        """Get overview of scenario usage across clusters.

        :return: Dictionary mapping scenario names to cluster IDs
        :rtype: dict[str, list[int]]
        """
        scenarios_map = {scenario_name: [] for scenario_name in self.list_scenarios()}
        data = list(
            self.user_cluster_mgr.collection.aggregate(
                MongoQueries.scenario_usage_overview()
            )
        )
        for item in data:
            scenarios_map[item["_id"]] = item["clusters"]
        return scenarios_map

    def scenario_usage(self, scenario_name: str) -> list:
        """Get all clusters using a specific scenario.

        :param scenario_name: Name of the scenario
        :type scenario_name: str
        :return: List of UserCluster objects using the scenario
        :rtype: list
        """
        return list(
            self.user_cluster_mgr.collection.find(
                {f"scenario_configs.{scenario_name}": {"$exists": True}}
            )
        )

    def delete_scenario(self, scenario_name: str):
        """Delete a scenario template.

        :param scenario_name: Name of scenario to delete
        :type scenario_name: str
        :raises ScenarioNotExistException: If scenario does not exist
        """
        path = self.get_scenario_dir(scenario_name)
        shutil.rmtree(path)
