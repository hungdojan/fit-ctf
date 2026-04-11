"""Docker/Podman helpers and polling used only by container integration tests."""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest


def container_client_kind() -> str:
    """Return ``docker`` or ``podman`` from env; skip if unset, mock, or unsupported."""
    raw = os.environ.get("CONTAINER_CLIENT", "docker").strip().lower()
    if raw in ("", "mock"):
        pytest.skip(
            "CONTAINER_CLIENT must be docker or podman for this test (not mock). "
            "Set in .env or the environment."
        )
    if raw not in ("docker", "podman"):
        pytest.skip(f"CONTAINER_CLIENT must be docker or podman, got {raw!r}")
    if raw == "docker" and shutil.which("docker") is None:
        pytest.skip("docker not on PATH")
    if raw == "podman" and shutil.which("podman-compose") is None:
        pytest.skip("podman-compose not on PATH")
    return raw


def compose_exec_argv(
    client: str,
    compose_files: list[Path],
    service: str,
    remote_cmd: list[str],
) -> list[str]:
    if client == "podman":
        argv = ["podman-compose"]
        for f in compose_files:
            argv.extend(["-f", str(f.resolve())])
        argv.extend(["exec", "-T", service, *remote_cmd])
        return argv
    argv = ["docker", "compose"]
    for f in compose_files:
        argv.extend(["-f", str(f.resolve())])
    argv.extend(["exec", "-T", service, *remote_cmd])
    return argv


def curl_from_login_node(
    client: str, compose_files: list[Path], url: str
) -> subprocess.CompletedProcess:
    cmd = compose_exec_argv(
        client,
        compose_files,
        "login_node",
        ["curl", "-fsS", url],
    )
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


def wait_for_flag_from_login_node(
    client: str,
    compose_files: list[Path],
    expected_body: str,
    *,
    url: str = "http://webserver:8080/flag",
    timeout_sec: float = 120.0,
    sleep_sec: float = 2.0,
) -> str:
    deadline = time.monotonic() + timeout_sec
    last: subprocess.CompletedProcess | None = None
    while time.monotonic() < deadline:
        last = curl_from_login_node(client, compose_files, url)
        if last.returncode == 0:
            body = last.stdout.rstrip()
            if body == expected_body:
                return body
        time.sleep(sleep_sec)
    err = last.stderr if last is not None else "no subprocess result"
    raise AssertionError(
        f"curl from login_node did not return expected body within timeout; last={err!r}"
    )


async def wait_for_flag_from_login_node_async(
    client: str,
    compose_files: list[Path],
    expected_body: str,
    *,
    url: str = "http://webserver:8080/flag",
    timeout_sec: float = 120.0,
    sleep_sec: float = 2.0,
) -> str:
    deadline = time.monotonic() + timeout_sec
    last: subprocess.CompletedProcess | None = None
    while time.monotonic() < deadline:
        last = curl_from_login_node(client, compose_files, url)
        if last.returncode == 0:
            body = last.stdout.rstrip()
            if body == expected_body:
                return body
        await asyncio.sleep(sleep_sec)
    err = last.stderr if last is not None else "no subprocess result"
    raise AssertionError(
        f"curl from login_node did not return expected body within timeout; last={err!r}"
    )


async def wait_instance_running(tui_app, pilot, *, timeout_sec: float) -> None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if await tui_app.core_mgr.instance_is_running():
            return
        await pilot.pause(0.25)
    raise AssertionError(
        f"instance still not running after {timeout_sec}s "
        "(check compose / container logs)"
    )


async def wait_instance_stopped(tui_app, pilot, *, timeout_sec: float) -> None:
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        if not await tui_app.core_mgr.instance_is_running():
            return
        await pilot.pause(0.25)
    raise AssertionError(f"instance still running after {timeout_sec}s")


def tcp_probe_from_login_node(
    client: str,
    compose_files: list[Path],
    host: str,
    port: int,
) -> subprocess.CompletedProcess:
    inner = f"cat < /dev/null > /dev/tcp/{host}/{port}"
    cmd = compose_exec_argv(
        client,
        compose_files,
        "login_node",
        ["bash", "-lc", f"timeout 5 bash -c {inner!r}"],
    )
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)
