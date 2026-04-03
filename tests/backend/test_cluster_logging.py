"""Tests for cluster logging / verbose wiring."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture
def prj1_project_cluster(connected_data):
    ctf_app, _ = connected_data
    project = ctf_app.prj_mgr.get_project("prj1")
    return ctf_app, ctf_app.project_cluster_mgr.get_cluster(project)


def test_build_cluster_images_verbose_passes_to_stdout(prj1_project_cluster):
    ctf_app, cluster = prj1_project_cluster
    mock_build = AsyncMock(return_value=0)
    with patch.object(ctf_app.c_client, "compose_build", mock_build):
        asyncio.run(
            ctf_app.project_cluster_mgr.build_cluster_images(cluster, verbose=True)
        )
    mock_build.assert_awaited_once()
    assert mock_build.await_args.kwargs.get("to_stdout") is True


def test_build_cluster_images_default_not_verbose(prj1_project_cluster):
    ctf_app, cluster = prj1_project_cluster
    mock_build = AsyncMock(return_value=0)
    with patch.object(ctf_app.c_client, "compose_build", mock_build):
        asyncio.run(ctf_app.project_cluster_mgr.build_cluster_images(cluster))
    assert mock_build.await_args.kwargs.get("to_stdout") is False


def test_project_start_cluster_verbose_passes_to_compose_up(prj1_project_cluster):
    ctf_app, cluster = prj1_project_cluster
    mock_up = AsyncMock(return_value=0)
    mock_running = AsyncMock(return_value=False)
    with (
        patch.object(ctf_app.c_client, "compose_up", mock_up),
        patch.object(
            ctf_app.project_cluster_mgr,
            "cluster_is_running",
            mock_running,
        ),
    ):
        asyncio.run(ctf_app.project_cluster_mgr.start_cluster(cluster, verbose=True))
    mock_up.assert_awaited_once()
    assert mock_up.await_args.kwargs.get("to_stdout") is True


def test_mock_client_compose_logs_api(connected_data):
    ctf_app, _ = connected_data
    code = asyncio.run(
        ctf_app.c_client.compose_logs(
            "prj1",
            [],
            tail=10,
            service=None,
            to_stdout=False,
        )
    )
    assert code == 0
