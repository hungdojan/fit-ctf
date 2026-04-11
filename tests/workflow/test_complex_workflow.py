"""Workflow1: CLI through user-cluster compile; assert compose and flag output."""

from jinja2 import Environment

from fit_ctf_components.data_parser.yaml_parser import YamlParser
from tests import ComplexData, fixture_path
from tests.workflow.workflow_helpers import (
    csv_data_rows,
    csv_dict_rows,
    run_cli,
    workflow1_setup_through_compile,
)


def test_workflow1(empty_complex: ComplexData):
    cli_run, tui_app, _path = empty_complex
    ctf_base = tui_app.core_mgr.ctf_base

    result = run_cli(cli_run, "project ls --format csv")
    assert not csv_data_rows(result.output)

    ctx = workflow1_setup_through_compile(cli_run, ctf_base)

    assert len([p for p in ctf_base.paths.project_global.iterdir() if p.is_dir()]) == 1
    assert len([u for u in ctf_base.paths.user_global.iterdir() if u.is_dir()]) == 1
    assert [
        m
        for m in ctf_base.paths.module_global.iterdir()
        if m.is_dir() and m.name == ctx.module["mn"]
    ]
    result = run_cli(cli_run, "scenario ls --format csv")
    data = [row["Name"] for row in csv_dict_rows(result.output)]
    assert len(data) == 4
    assert (ctf_base.paths.module_global / ctx.module["mn"] / "Containerfile").exists()
    assert ctx.enrolled_path.exists()

    assert ctx.new_scenario["n"] in ctx.cluster.scenario_names
    assert ctx.cluster.scenario_names == list(ctx.cluster.scenario_configs.keys())

    assert (ctx.enrolled_path / ctx.new_scenario["n"]).exists()
    assert ctx.compiled_file.exists()
    assert (
        ctx.compiled_file.read_text().rstrip()
        == (fixture_path() / "workflow1" / "expected_file").read_text().rstrip()
    )

    module_build_context = str(
        (ctf_base.paths.module_global / ctx.module["mn"]).resolve()
    )
    flag_volume_host = str(ctx.compiled_file.resolve())
    private_net = f"{ctx.prj['pn']}_{ctx.user['u']}_private_net"
    expected_tpl = Environment().from_string(
        (fixture_path() / "workflow1" / "expected_compose.yaml").read_text()
    )
    expected_compose_text = expected_tpl.render(
        module_build_context=module_build_context,
        flag_volume_host=flag_volume_host,
        private_net=private_net,
    )
    expected_compose = YamlParser.load_data_stream(expected_compose_text)
    assert ctx.compiled_scenario_path.exists()
    actual_compose = YamlParser.load_data_file(ctx.compiled_scenario_path)
    assert actual_compose == expected_compose
