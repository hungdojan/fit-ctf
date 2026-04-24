"""Scenario compile copies optional ``modules/`` from the template (like ``volumes/``)."""

from pathlib import Path

from fit_ctf.models.infra.config_models import ScenarioConfig
from fit_ctf.models.infra.scenario_compile import (
    ScenarioCompileContext,
    ScenarioCompiler,
)


def _minimal_paths(tmp: Path) -> dict[str, Path]:
    share = tmp / "share"
    return {
        "projects": share / "project",
        "users": share / "user",
        "modules": share / "module",
        "scenarios": share / "scenarios",
    }


def test_scenario_compile_copies_volumes_and_modules_trees(tmp_path: Path):
    paths = _minimal_paths(tmp_path)
    scenario_dir = paths["scenarios"] / "s1"
    scenario_dir.mkdir(parents=True)
    (scenario_dir / "scenario_compose.yaml.j2").write_text(
        "---\nname: s1\nservices: {}\n"
    )
    (scenario_dir / "volumes" / "data").mkdir(parents=True)
    (scenario_dir / "volumes" / "data" / "v.txt").write_text("v")
    (scenario_dir / "modules" / "my_build").mkdir(parents=True)
    (scenario_dir / "modules" / "my_build" / "Marker").write_text("ok")

    dest = paths["projects"] / "prj" / "scenarios" / "s1"
    cfg = ScenarioConfig(scenario_name="s1", service_configs={})
    ctx = ScenarioCompileContext(
        paths_dict=paths,
        scenario_global_root=scenario_dir,
        compile_destination_root=dest,
        network_map={},
        volume_context_extras={
            "project_scenario_dir": str(dest),
            "project_name": "prj",
        },
    )
    ScenarioCompiler(ctx).compile(cfg, {"project_name": "prj"})

    assert (dest / "volumes" / "data" / "v.txt").read_text() == "v"
    assert (dest / "modules" / "my_build" / "Marker").read_text() == "ok"
