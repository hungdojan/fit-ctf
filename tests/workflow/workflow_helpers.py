"""Shared CLI steps and assertions for workflow1 / workflow2 integration tests."""

from __future__ import annotations

import csv
import os
import shutil
from io import StringIO
from types import SimpleNamespace
from typing import Any

from click.testing import CliRunner, Result

from fit_ctf.components.data_parser.yaml_parser import YamlParser
from fit_ctf.models.infra.config_models import (
    scenario_config_from_dict,
    validate_canonical_scenario_yaml_dict,
)
from fit_ctf_cli.cli import cli
from tests import fixture_path


def is_container_client_testing_enabled() -> bool:
    return os.getenv("ENABLE_CONTAINER_CLIENT_TESTING", "0") != "0"


def run_cli(runner: CliRunner, cmd: str) -> Result:
    result = runner.invoke(cli, cmd)
    assert result.exit_code == 0
    return result


def csv_data_rows(result_output: str) -> list[list[str]]:
    f = StringIO(result_output)
    return [row for row in csv.reader(f)][1:]


def csv_dict_rows(result_output: str) -> list[dict[str, str]]:
    f = StringIO(result_output)
    return list(csv.DictReader(f))


def service_network_ids(service: dict[str, Any]) -> set[str]:
    """Compose ``networks`` for a service may be a mapping or a list of names."""
    raw = service.get("networks")
    if raw is None:
        return set()
    if isinstance(raw, dict):
        return set(raw.keys())
    if isinstance(raw, list):
        names: set[str] = set()
        for item in raw:
            if isinstance(item, str):
                names.add(item)
            elif isinstance(item, dict):
                names.update(item.keys())
        return names
    return set()


def workflow1_setup_through_compile(cli_run: CliRunner, ctf_base) -> SimpleNamespace:
    """CLI setup through user-cluster compile (shared by unit-style and container tests)."""
    expect_data = {
        "projects": {"prj1": {"pn": "prj1"}},
        "users": {"user1": {"u": "user1", "p": "user1Password"}},
        "modules": {"webserver": {"mn": "webserver"}},
        "scenarios": {"new_node": {"n": "new_node"}},
    }

    prj = expect_data["projects"]["prj1"]
    run_cli(cli_run, f"project create -pn {prj['pn']}")

    user = expect_data["users"]["user1"]
    run_cli(cli_run, f"user create -u {user['u']} -p {user['p']} --format csv")

    module = expect_data["modules"]["webserver"]
    run_cli(cli_run, f"module create -mn {module['mn']}")

    module_dir = ctf_base.paths.module_global / module["mn"]
    shutil.copy(
        fixture_path() / "workflow1" / "webserver.Containerfile",
        module_dir / "Containerfile",
    )

    if is_container_client_testing_enabled():
        run_cli(cli_run, f"module build -mn {module['mn']}")

    new_scenario = expect_data["scenarios"]["new_node"]
    run_cli(cli_run, f"scenario create -n {new_scenario['n']}")

    scenario_dir = ctf_base.paths.scenario_global / new_scenario["n"]
    for file in (scenario_dir / "volumes").iterdir():
        if file.is_file():
            file.unlink()

    shutil.copy(
        fixture_path() / "workflow1" / "new_node_scenario_template.yaml.j2",
        scenario_dir / "scenario_compose.yaml.j2",
    )
    shutil.copy(
        fixture_path() / "workflow1" / "flag.template",
        scenario_dir / "volumes" / "flag.template",
    )

    run_cli(
        cli_run,
        f"enrollment enroll -u {user['u']} -pn {prj['pn']} --login-node-type ssh_ubi",
    )
    enrolled_path = ctf_base.paths.enrolled_user_path(
        ctf_base.user_mgr.get_user(user["u"]), ctf_base.prj_mgr.get_project(prj["pn"])
    )
    run_cli(cli_run, f"scenario vars-template -n {new_scenario['n']}")

    scenario_config_path = fixture_path() / "workflow1" / "scenario_config.yaml"
    run_cli(
        cli_run,
        "user-cluster add-scenario "
        f"-u {user['u']} "
        f"-pn {prj['pn']} "
        f"-s {new_scenario['n']} "
        f"-f {scenario_config_path}",
    )

    run_cli(
        cli_run,
        f"user-cluster compile -u {user['u']} -pn {prj['pn']} ",
    )

    u_obj = ctf_base.user_mgr.get_user(user["u"])
    p_obj = ctf_base.prj_mgr.get_project(prj["pn"])
    enrollment = ctf_base.enroll_mgr.get_enrollment(u_obj, p_obj)
    cluster = ctf_base.user_cluster_mgr.get_cluster(enrollment)

    compiled_file = enrolled_path / new_scenario["n"] / "volumes" / "flag"
    compiled_scenario_path = enrolled_path / new_scenario["n"] / "scenario_compose.yaml"

    return SimpleNamespace(
        expect_data=expect_data,
        prj=prj,
        user=user,
        module=module,
        new_scenario=new_scenario,
        enrolled_path=enrolled_path,
        compiled_file=compiled_file,
        compiled_scenario_path=compiled_scenario_path,
        cluster=cluster,
        u_obj=u_obj,
        p_obj=p_obj,
        enrollment=enrollment,
    )


def workflow2_setup_through_compile(cli_run: CliRunner, ctf_base) -> SimpleNamespace:
    """Workflow1 path plus project ``template`` and ``proj_webserver`` scenarios compiled."""
    ctx = workflow1_setup_through_compile(cli_run, ctf_base)

    proj_web_name = "proj_webserver"
    run_cli(cli_run, f"scenario create -n {proj_web_name}")
    proj_web_dir = ctf_base.paths.scenario_global / proj_web_name
    for file in (proj_web_dir / "volumes").iterdir():
        if file.is_file():
            file.unlink()
    shutil.copy(
        fixture_path() / "workflow2" / "project_webserver_scenario_compose.yaml.j2",
        proj_web_dir / "scenario_compose.yaml.j2",
    )
    shutil.copy(
        fixture_path() / "workflow1" / "flag.template",
        proj_web_dir / "volumes" / "flag.template",
    )

    pc = ctf_base.project_cluster_mgr.get_cluster(ctx.p_obj)

    for rel_path, scenario_key in (
        ("workflow2/project_template_config.yaml", "template"),
        ("workflow2/project_webserver_config.yaml", proj_web_name),
    ):
        raw = YamlParser.load_data_file(fixture_path() / rel_path)
        validate_canonical_scenario_yaml_dict(raw)
        proj_cfg = scenario_config_from_dict(scenario_key, raw)
        ctf_base.project_cluster_mgr.create_or_update_scenario_config(pc, proj_cfg)

    pc = ctf_base.project_cluster_mgr.get_cluster(ctx.p_obj)
    project_template_compose = (
        ctf_base.paths.project_scenarios(ctx.p_obj) / "template" / "scenario_compose.yaml"
    )
    project_webserver_compose = (
        ctf_base.paths.project_scenarios(ctx.p_obj) / proj_web_name / "scenario_compose.yaml"
    )

    return SimpleNamespace(
        **{k: v for k, v in vars(ctx).items()},
        project_cluster=pc,
        project_template_compose=project_template_compose,
        project_webserver_compose=project_webserver_compose,
        proj_webserver_name=proj_web_name,
    )
