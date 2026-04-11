"""Shared scenario template compilation (project and user clusters)."""

from __future__ import annotations

import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fit_ctf_models.clusters.config_models import ScenarioConfig
from fit_ctf_templates import (
    get_template,
    materialize_volume_src_for_compose,
    resolve_volume_src_path,
    validate_variable_parse,
)

__all__ = ["ScenarioCompileContext", "ScenarioCompiler"]


@dataclass(frozen=True, slots=True)
class ScenarioCompileContext:
    """Immutable inputs for compiling one scenario into a destination tree."""

    paths_dict: Mapping[str, Path]
    scenario_global_root: Path
    compile_destination_root: Path
    network_map: Mapping[str, str]
    volume_context_extras: Mapping[str, Any]


class ScenarioCompiler:
    """Copy scenario assets, build compose param map, and render `scenario_compose.yaml`.

    ``ScenarioConfig.secrets`` is injected only into ``volumes/*.template`` render
    contexts as ``secret_map__<name>`` (alongside ``{service}__volume_map__{vol}__*`` from
    ``template_params``), not into ``src_path`` or ``scenario_compose.yaml.j2``.
    """

    def __init__(self, context: ScenarioCompileContext) -> None:
        self._c = context

    def copy_scenario_template_trees(self) -> None:
        """Copy `volumes/` and, `modules/` from the scenario template (not stored in DB)."""
        self._c.compile_destination_root.mkdir(parents=True, exist_ok=True)
        root = self._c.scenario_global_root
        dst = self._c.compile_destination_root
        for name in ("volumes", "modules"):
            src = root / name
            if src.is_dir():
                shutil.copytree(src, dst / name, dirs_exist_ok=True)

    def _volume_src_path_context(self) -> dict[str, Any]:
        """Context for resolving ``volume_map.src_path`` Jinja only (not the compose param map)."""
        scenario_dir_s = str(self._c.scenario_global_root.resolve())
        ctx: dict[str, Any] = {
            **{f"paths__{k}": str(v) for k, v in self._c.paths_dict.items()},
            "scenario_dir": scenario_dir_s,
            **dict(self._c.volume_context_extras),
        }
        # Same directory as ``scenario_dir``; overrides ``paths__scenarios`` from ``paths_dict``
        # for this pass so ``src_path`` can use ``{{ paths__scenarios }}/volumes/...``.
        ctx["paths__scenarios"] = scenario_dir_s
        return ctx

    def build_param_map(self, scenario_config: ScenarioConfig) -> dict[str, Any]:
        """Assemble the param dict passed to `scenario_compose.yaml.j2`."""
        dyn = dict(scenario_config.secrets)
        base_vol = self._volume_src_path_context()
        param_map: dict[str, Any] = {
            **{f"paths__{k}": str(v) for k, v in self._c.paths_dict.items()},
            **{f"network_map__{k}": v for k, v in self._c.network_map.items()},
        }
        for s_name, s_content in scenario_config.service_configs.items():
            for vol_name, config in s_content.volume_map.items():
                resolved = resolve_volume_src_path(config.src_path, base_vol)
                param_map[f"{s_name}__volume_map__{vol_name}"] = (
                    materialize_volume_src_for_compose(
                        resolved,
                        scenario_root=self._c.scenario_global_root,
                        compile_dst_root=self._c.compile_destination_root,
                        service_name=s_name,
                        volume_name=vol_name,
                        template_params=config.template_params,
                        secrets=dyn,
                    )
                )
            param_map.update(
                {f"{s_name}__env_map__{k}": v for k, v in s_content.env_map.items()}
            )
            param_map.update(
                {f"{s_name}__port_map__{k}": v for k, v in s_content.port_map.items()}
            )
        return param_map

    def write_compose(
        self,
        param_map: Mapping[str, Any],
        compose_template_extras: Mapping[str, Any],
    ) -> None:
        """Merge extras into `param_map`, validate, and write `scenario_compose.yaml`."""
        merged = {**dict(param_map), **dict(compose_template_extras)}
        root = self._c.scenario_global_root
        template = get_template("scenario_compose.yaml.j2", str(root.resolve()))
        validate_variable_parse("scenario_compose.yaml.j2", root, merged)
        self._c.compile_destination_root.mkdir(parents=True, exist_ok=True)
        out = self._c.compile_destination_root / "scenario_compose.yaml"
        with open(out, "w") as f:
            f.write(template.render(**merged))

    def compile(
        self,
        scenario_config: ScenarioConfig,
        compose_template_extras: Mapping[str, Any],
    ) -> None:
        """Run copy, param map build, and compose render in order."""
        self.copy_scenario_template_trees()
        param_map = self.build_param_map(scenario_config)
        self.write_compose(param_map, compose_template_extras)
