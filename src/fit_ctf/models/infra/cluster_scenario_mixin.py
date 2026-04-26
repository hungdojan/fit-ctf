from __future__ import annotations

import logging
import shutil
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, TypeVar, cast

from pydantic import Field

from fit_ctf.models.base import Base, BaseManagerInterface
from fit_ctf.models.infra.config_models import ScenarioConfig
from fit_ctf.models.infra.constants import CLUSTER_LOGGER_NAME
from fit_ctf.models.infra.scenario_compile import (
    ScenarioCompileContext,
    ScenarioCompiler,
)
from fit_ctf.models.infra.scenario_manager import ScenarioManager
from fit_ctf.models.utils.exceptions import ScenarioNotExistException


class BaseCluster(Base):
    """Base for cluster documents with scenario configuration (DB + compile)."""

    name: str
    scenario_configs: dict[str, ScenarioConfig] = Field(default_factory=dict)
    scenario_names: list[str] = Field(default_factory=list)


ClusterT = TypeVar("ClusterT", bound=BaseCluster)


class ClusterScenarioMixin(BaseManagerInterface[ClusterT], ABC):
    """Template-method helpers: subclasses implement path/network hooks.

    Concrete managers inherit this mixin only; it extends
    :class:`BaseManagerInterface` for ``paths``, ``update_doc``, and collection access.
    """

    @abstractmethod
    def _scenario_global_and_destination(
        self, cluster: ClusterT, scenario_name: str
    ) -> tuple[Path, Path]:
        """Return ``(scenario_global_root, compile_destination_root)`` for ``scenario_name``."""

    @abstractmethod
    def _network_map_for_scenario_compile(self, cluster: ClusterT) -> Mapping[str, str]:
        """Network names for compose param map (``network_map__*``)."""

    @abstractmethod
    def _volume_context_extras(
        self, cluster: ClusterT, compile_destination: Path
    ) -> Mapping[str, Any]:
        """Extra Jinja keys for ``volume_map.src_path`` (e.g. ``project_scenario_dir``)."""

    @abstractmethod
    def _compose_template_extras(self, cluster: ClusterT) -> Mapping[str, Any]:
        """Keys merged into the compose template render (e.g. ``project_name``, ``username``)."""

    def create_or_update_scenario_config(
        self,
        cluster: ClusterT,
        scenario_config: ScenarioConfig,
        *,
        template_warning_sink: Callable[[str], None] | None = None,
    ) -> None:
        cluster.scenario_configs[scenario_config.scenario_name] = scenario_config
        cluster.scenario_names = list(cluster.scenario_configs.keys())
        self.update_doc(cluster)
        self.compile_scenario(
            cluster,
            scenario_config.scenario_name,
            template_warning_sink=template_warning_sink,
        )

    def compile_scenario(
        self,
        cluster: ClusterT,
        scenario_name: str,
        *,
        template_warning_sink: Callable[[str], None] | None = None,
    ) -> None:
        if scenario_name not in cluster.scenario_configs:
            raise ScenarioNotExistException(
                f"Scenario {scenario_name} not found in {cluster.name}"
            )
        scenario_cfg = cluster.scenario_configs[scenario_name]
        # Create temporary ScenarioManager for validation
        sm = ScenarioManager(paths=self.paths)
        warnings = sm.validate_scenario_config_against_templates(
            scenario_name, scenario_cfg
        )
        log = logging.getLogger(CLUSTER_LOGGER_NAME)
        for w in warnings:
            if template_warning_sink is not None:
                template_warning_sink(w)
            else:
                log.warning(w)
        src_path, dst_path = self._scenario_global_and_destination(
            cluster, scenario_name
        )
        compile_ctx = ScenarioCompileContext(
            paths_dict=cast(Mapping[str, Path], self.paths.paths_dict),
            scenario_global_root=src_path,
            compile_destination_root=dst_path,
            network_map=self._network_map_for_scenario_compile(cluster),
            volume_context_extras=self._volume_context_extras(cluster, dst_path),
        )
        ScenarioCompiler(compile_ctx).compile(
            scenario_cfg,
            compose_template_extras=self._compose_template_extras(cluster),
        )

    def remove_scenario_config(self, cluster: ClusterT, scenario_name: str) -> None:
        if scenario_name in cluster.scenario_configs:
            cluster.scenario_configs.pop(scenario_name)
            cluster.scenario_names.remove(scenario_name)
            self.update_doc(cluster)
        _, dst_path = self._scenario_global_and_destination(cluster, scenario_name)
        if dst_path.exists() and dst_path.is_dir():
            shutil.rmtree(dst_path)
