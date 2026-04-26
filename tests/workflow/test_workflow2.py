"""Workflow2: project ``template`` + ``proj_webserver`` on top of workflow1 user stack.

``proj_webserver`` is the webserver module on the project shared network (service name
``project_webserver``) so it does not collide with the user's ``webserver`` on the
private network. ``login_node`` can reach Mongo on ``template_service`` and HTTP on
``project_webserver`` when stacks run (see container test).
"""

from __future__ import annotations

from fit_ctf.components.data_parser.yaml_parser import YamlParser
from tests import ComplexData
from tests.workflow.workflow_helpers import (
    run_cli,
    service_network_ids,
    workflow2_setup_through_compile,
)


def test_workflow2_project_and_user_compiled(empty_complex: ComplexData):
    """Project ``template`` + user ``login_node`` / ``new_node``; shared net links them."""
    cli_run, tui_app, _path = empty_complex
    ctf_base = tui_app.core_mgr.ctf_base

    run_cli(cli_run, "project ls --format csv")

    w2 = workflow2_setup_through_compile(cli_run, ctf_base)

    assert "template" in w2.project_cluster.scenario_names
    assert w2.proj_webserver_name in w2.project_cluster.scenario_names
    assert w2.project_cluster.scenario_names == list(w2.project_cluster.scenario_configs.keys())
    assert w2.project_template_compose.exists()
    assert w2.project_webserver_compose.exists()

    user_cluster = ctf_base.user_cluster_mgr.get_cluster(w2.enrollment)
    assert "login_node" in user_cluster.scenario_names
    assert w2.new_scenario["n"] in user_cluster.scenario_names

    pmap = ctf_base.project_cluster_mgr.get_network_map(w2.p_obj)
    umap = ctf_base.user_cluster_mgr.get_network_map((w2.u_obj, w2.p_obj))
    assert pmap["shared"] == umap["shared"], (
        "user and project must share the same shared network name"
    )

    proj_compose = YamlParser.load_data_file(w2.project_template_compose)
    tpl_svc = proj_compose["services"]["template_service"]
    assert pmap["shared"] in service_network_ids(tpl_svc)

    web_compose = YamlParser.load_data_file(w2.project_webserver_compose)
    pws = web_compose["services"]["project_webserver"]
    assert pmap["shared"] in service_network_ids(pws)

    login_compose_path = w2.enrolled_path / "login_node" / "scenario_compose.yaml"
    assert login_compose_path.exists()
    login_compose = YamlParser.load_data_file(login_compose_path)
    login_svc = login_compose["services"]["login_node"]
    assert pmap["shared"] in service_network_ids(login_svc)

    assert w2.compiled_file.exists()
