"""End-to-end container checks for workflow1 and workflow2.

One workflow1 variant drives :class:`fit_ctf_rendezvous.rendezvous_app.RendezvousApp`
with Textual ``run_test`` / ``pilot`` (login, select project, Project Info, Start/Stop)
so the same :meth:`~fit_ctf_rendezvous.rendezvous_core.RendezvousCore.start_user_instance`
path runs as in the real TUI.

Workflow2 adds project ``template`` (Mongo) and ``proj_webserver`` on the shared net;
``user-cluster start`` brings the project stack up first, then the user stack.

Requires: MongoDB (``empty_complex``), ``ENABLE_CONTAINER_CLIENT_TESTING=1``, and
``CONTAINER_CLIENT`` set to ``docker`` or ``podman`` in the environment or ``.env``
(not ``mock``). Matches the runtime used by ``CTFApp`` / cluster managers.

- **docker:** ``docker`` and ``docker compose`` on ``PATH``
- **podman:** ``podman-compose`` on ``PATH`` (same as ``PodmanClient``)

pyproject defaults ``CONTAINER_CLIENT=mock``; use ``D:CONTAINER_CLIENT=mock`` so a
shell or ``.env`` value overrides, or export before pytest.

Building ``login_node`` pulls UBI9 and runs ``dnf``; corporate proxies or SSL
interception may require extra configuration.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from dotenv import load_dotenv
from textual.widgets import Input

from fit_ctf_rendezvous.screens.app_screen.app_screen import AppScreen
from tests import ComplexData, fixture_path
from tests.workflow.container_helpers import (
    container_client_kind,
    tcp_probe_from_login_node,
    wait_for_flag_from_login_node,
    wait_for_flag_from_login_node_async,
    wait_instance_running,
    wait_instance_stopped,
)
from tests.workflow.workflow_helpers import (
    run_cli,
    workflow1_setup_through_compile,
    workflow2_setup_through_compile,
)

if os.getenv("ENABLE_CONTAINER_CLIENT_TESTING", "0") == "0":
    pytest.skip("Container testing not enabled.", allow_module_level=True)

load_dotenv()


def _expected_flag_body(rel_fixture: str) -> str:
    return (fixture_path() / rel_fixture).read_text().rstrip()


def _ctf_from_empty_complex(empty_complex: ComplexData):
    cli_run, tui_app, _path = empty_complex
    return cli_run, tui_app.core_mgr.ctf_base


@pytest.mark.integration
def test_workflow1_login_node_fetches_flag_over_http(empty_complex: ComplexData):
    """Build user cluster images, start stack, curl /flag from login_node; match expected_file."""
    client_kind = container_client_kind()
    cli_run, ctf_base = _ctf_from_empty_complex(empty_complex)

    run_cli(cli_run, "project ls --format csv")
    ctx = workflow1_setup_through_compile(cli_run, ctf_base)

    cluster = ctf_base.user_cluster_mgr.get_cluster(ctx.enrollment)
    compose_files = ctf_base.user_cluster_mgr.get_compose_files(cluster)
    assert ctx.new_scenario["n"] in cluster.scenario_names
    assert len(compose_files) >= 2

    expected_body = _expected_flag_body("workflow1/expected_file")

    try:
        build_code = asyncio.run(
            ctf_base.user_cluster_mgr.build_cluster_images(cluster, verbose=False)
        )
        assert build_code == 0, f"compose build failed with {build_code}"

        start_code = asyncio.run(ctf_base.user_cluster_mgr.start_cluster(cluster, verbose=False))
        assert start_code == 0, f"compose up failed with {start_code}"

        body = wait_for_flag_from_login_node(client_kind, compose_files, expected_body)
        assert body == expected_body
    finally:
        asyncio.run(ctf_base.user_cluster_mgr.stop_cluster(cluster, verbose=False))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow1_rendezvous_ui_start_instance_fetches_flag(
    empty_complex: ComplexData,
):
    """Workflow1 stack: build images, then start instance via Rendezvous UI (pilot clicks)."""
    client_kind = container_client_kind()
    cli_run, tui_app, _path = empty_complex
    ctf_base = tui_app.core_mgr.ctf_base

    run_cli(cli_run, "project ls --format csv")
    ctx = workflow1_setup_through_compile(cli_run, ctf_base)

    cluster = ctf_base.user_cluster_mgr.get_cluster(ctx.enrollment)
    compose_files = ctf_base.user_cluster_mgr.get_compose_files(cluster)
    assert ctx.new_scenario["n"] in cluster.scenario_names
    assert len(compose_files) >= 2

    expected_body = _expected_flag_body("workflow1/expected_file")

    build_code = await ctf_base.user_cluster_mgr.build_cluster_images(cluster, verbose=False)
    assert build_code == 0, f"compose build failed with {build_code}"

    prj_btn_id = f"#select-btn-{ctx.prj['pn']}"

    try:
        async with tui_app.run_test() as pilot:
            tui_app.screen.query_one("#login-username-input", Input).value = ctx.user["u"]
            tui_app.screen.query_one("#login-password-input", Input).value = ctx.user["p"]
            await pilot.click("#login-submit-btn")
            await pilot.pause(0.2)
            assert isinstance(tui_app.screen, AppScreen)

            await pilot.click("#sidebar-select-project-btn")
            await pilot.pause(0.25)
            await pilot.click(prj_btn_id)
            await pilot.pause(0.2)

            await pilot.click("#sidebar-project-info-btn")
            await pilot.pause(0.3)

            await pilot.click("#projectinfo-toggle-instance-btn")
            await wait_instance_running(tui_app, pilot, timeout_sec=180.0)

            body = await wait_for_flag_from_login_node_async(
                client_kind, compose_files, expected_body
            )
            assert body == expected_body

            await pilot.click("#projectinfo-toggle-instance-btn")
            await wait_instance_stopped(tui_app, pilot, timeout_sec=120.0)
    finally:
        asyncio.run(ctf_base.user_cluster_mgr.stop_cluster(cluster, verbose=False))


@pytest.mark.integration
def test_workflow2_project_template_and_user_flag(empty_complex: ComplexData):
    """User private webserver + project shared ``project_webserver`` + project Mongo."""
    client_kind = container_client_kind()
    cli_run, ctf_base = _ctf_from_empty_complex(empty_complex)

    run_cli(cli_run, "project ls --format csv")
    w2 = workflow2_setup_through_compile(cli_run, ctf_base)

    user_cluster = ctf_base.user_cluster_mgr.get_cluster(w2.enrollment)
    project_cluster = ctf_base.project_cluster_mgr.get_cluster(w2.p_obj)
    compose_files = ctf_base.user_cluster_mgr.get_compose_files(user_cluster)
    assert "template" in project_cluster.scenario_names
    assert w2.proj_webserver_name in project_cluster.scenario_names
    assert "login_node" in user_cluster.scenario_names
    assert w2.new_scenario["n"] in user_cluster.scenario_names
    assert len(compose_files) >= 2

    expected_body = _expected_flag_body("workflow2/expected_file")
    proj_flag_url = "http://project_webserver:8080/flag"

    try:
        build_code = asyncio.run(
            ctf_base.user_cluster_mgr.build_cluster_images(user_cluster, verbose=False)
        )
        assert build_code == 0, f"compose build failed with {build_code}"

        start_code = asyncio.run(
            ctf_base.user_cluster_mgr.start_cluster(user_cluster, verbose=False)
        )
        assert start_code == 0, f"compose up failed with {start_code}"

        body = wait_for_flag_from_login_node(client_kind, compose_files, expected_body)
        assert body == expected_body

        tcp = tcp_probe_from_login_node(client_kind, compose_files, "template_service", 27017)
        assert tcp.returncode == 0, (
            "login_node should reach project template_service Mongo on 27017 "
            f"(stderr={tcp.stderr!r})"
        )

        proj_body = wait_for_flag_from_login_node(
            client_kind,
            compose_files,
            expected_body,
            url=proj_flag_url,
            timeout_sec=60.0,
        )
        assert proj_body == expected_body
    finally:
        asyncio.run(ctf_base.user_cluster_mgr.stop_cluster(user_cluster, verbose=False))
        asyncio.run(ctf_base.project_cluster_mgr.stop_cluster(project_cluster, verbose=False))
