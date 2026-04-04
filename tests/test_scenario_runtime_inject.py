"""Inject scenario trees at runtime by copying `tests/fixtures/injected_scenarios/*`.

Edit files under `fixtures/injected_scenarios/<name>/` (compose, `volumes/`, etc.)
instead of large inline strings in this module.
"""

from __future__ import annotations

import shutil
from types import SimpleNamespace
from pathlib import Path

import pytest

from tests import fixture_path

from fit_ctf_models.clusters.config_models import (
    ScenarioConfig,
    ServiceConfig,
    VolumeConfig,
    scenario_config_from_dict,
)
from fit_ctf_models.clusters.scenario_compile import (
    ScenarioCompileContext,
    ScenarioCompiler,
)
from fit_ctf_models.clusters.scenario_manager import ScenarioManager
from fit_ctf_models.utils.exceptions import ScenarioNotExistException

INJECTED_SCENARIOS = fixture_path() / "injected_scenarios"


def copy_injected_scenario(
    scenarios_root: Path,
    fixture_name: str,
    *,
    dest_name: str | None = None,
) -> Path:
    """Copy `fixtures/injected_scenarios/<fixture_name>` into `scenarios_root/<dest_name>`.

    `dest_name` defaults to `fixture_name` (same folder name under the temp scenarios root).
    """
    src = INJECTED_SCENARIOS / fixture_name
    if not src.is_dir():
        raise FileNotFoundError(f"Missing injected scenario fixture directory: {src}")
    dst = scenarios_root / (dest_name or fixture_name)
    shutil.copytree(src, dst)
    return dst


@pytest.fixture
def injected_scenarios_source() -> Path:
    """Path to the repo's `tests/fixtures/injected_scenarios` tree (read-only)."""
    return INJECTED_SCENARIOS


def scenario_manager_for_scenarios_root(scenarios_root: Path) -> ScenarioManager:
    """Build a :class:`ScenarioManager`
    whose scenario root is `scenarios_root` (no DB / full CTFApp).
    """
    base = SimpleNamespace(paths=SimpleNamespace(scenario_global=scenarios_root))
    return ScenarioManager(base)  # type: ignore[arg-type]


def test_inject_fetch_variables_port_env_volume(tmp_path: Path):
    copy_injected_scenario(tmp_path, "s_port")
    mgr = scenario_manager_for_scenarios_root(tmp_path)
    vd = mgr.fetch_variables("s_port")
    assert vd["web"]["port_map"]["http"] == ""
    assert vd["web"]["env_map"]["K"] == ""
    assert vd["web"]["volume_map"]["data"]["src_path"] == ""


def test_inject_fetch_variables_volume_template_params(tmp_path: Path):
    copy_injected_scenario(tmp_path, "s_tpl")
    mgr = scenario_manager_for_scenarios_root(tmp_path)
    vd = mgr.fetch_variables("s_tpl")
    assert vd["app"]["volume_map"]["vol"]["template_params"]["secret"] == ""


def test_inject_list_scenarios(tmp_path: Path):
    copy_injected_scenario(tmp_path, "minimal", dest_name="alpha")
    copy_injected_scenario(tmp_path, "minimal", dest_name="beta")
    names = sorted(scenario_manager_for_scenarios_root(tmp_path).list_scenarios())
    assert names == ["alpha", "beta"]


def test_inject_get_scenario_dir_missing(tmp_path: Path):
    mgr = scenario_manager_for_scenarios_root(tmp_path)
    with pytest.raises(ScenarioNotExistException):
        mgr.get_scenario_dir("nope")


def test_inject_scenario_config_from_dict_roundtrip_build_param_map(tmp_path: Path):
    """YAML-shaped dict → ScenarioConfig → param keys match compose variables from fixture."""
    scenario_dir = copy_injected_scenario(tmp_path, "s_round")
    raw = {
        "service_configs": {
            "api": {
                "port_map": {"ssh": 2222},
                "env_map": {},
                "volume_map": {},
            }
        }
    }
    cfg = scenario_config_from_dict("s_round", raw)
    paths = {
        "projects": tmp_path / "p",
        "users": tmp_path / "u",
        "modules": tmp_path / "m",
        "scenarios": tmp_path / "scenarios",
    }
    dest = paths["projects"] / "prj" / "scenarios" / "s_round"
    ctx = ScenarioCompileContext(
        paths_dict=paths,
        scenario_global_root=scenario_dir,
        compile_destination_root=dest,
        network_map={},
        volume_context_extras={"project_name": "prj"},
    )
    pm = ScenarioCompiler(ctx).build_param_map(cfg)
    assert pm["api__port_map__ssh"] == 2222


def test_inject_full_compile_writes_compose(tmp_path: Path):
    """End-to-end compile using `s_full` fixture → `scenario_compose.yaml` on disk."""
    scenario_dir = copy_injected_scenario(tmp_path, "s_full")

    cfg = ScenarioConfig(
        scenario_name="s_full",
        service_configs={
            "web": ServiceConfig(
                port_map={"http": 18080},
                env_map={"FLAG": "yes"},
                volume_map={
                    "blob": VolumeConfig(
                        src_path="{{ scenario_dir }}/volumes/blob.txt",
                        template_params={},
                    )
                },
            )
        },
    )
    paths = {
        "projects": tmp_path / "p",
        "users": tmp_path / "u",
        "modules": tmp_path / "m",
        "scenarios": tmp_path / "scenarios",
    }
    dest = paths["projects"] / "demo" / "scenarios" / "s_full"
    ctx = ScenarioCompileContext(
        paths_dict=paths,
        scenario_global_root=scenario_dir,
        compile_destination_root=dest,
        network_map={"shared": "demo_shared_net"},
        volume_context_extras={
            "project_name": "demo",
            "project_scenario_dir": str(dest),
        },
    )
    ScenarioCompiler(ctx).compile(cfg, {"project_name": "demo"})

    out = (dest / "scenario_compose.yaml").read_text(encoding="utf-8")
    assert "18080:80" in out
    assert "FLAG=yes" in out
    assert "/blob:ro" in out
    assert "demo_shared_net" in out
    assert "demo_full" in out


def test_injected_scenarios_fixture_tree_exists(injected_scenarios_source: Path):
    """Sanity check: expected fixture dirs are present for contributors."""
    for name in ("s_port", "s_tpl", "minimal", "s_round", "s_full"):
        assert (injected_scenarios_source / name / "scenario_compose.yaml.j2").is_file()
