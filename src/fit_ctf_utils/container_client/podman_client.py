import json

# import subprocess
import subprocess
import sys
from logging import Logger
from pathlib import Path
from typing import Any

import fit_ctf_utils
from fit_ctf_utils.container_client.container_client_interface import (
    ContainerClientInterface,
)
from fit_ctf_utils.types import HealthCheckDict


class PodmanClient(ContainerClientInterface):

    @classmethod
    def generate_container_prefix(cls, *names: str) -> str:
        return f"{'_'.join(names)}_"

    @classmethod
    async def get_images(cls, contains: str | list[str] | None = None) -> list[str]:
        cmd = ["podman", "images", "--format", '"{{ .Repository }}"']
        return await cls._process_get_commands(cmd, contains)

    @classmethod
    async def get_networks(cls, contains: str | list[str] | None = None) -> list[str]:
        cmd = ["podman", "network", "ls", "--format", '"{{.Name}}"']
        return await cls._process_get_commands(cmd, contains)

    @classmethod
    async def rm_images(
        cls, logger: Logger, contains: str | list[str], to_stdout: bool = False
    ) -> int:
        images = await cls.get_images(contains)
        if not images:
            return -1
        cmd = ["podman", "rmi"] + images
        proc, stdout = await fit_ctf_utils.create_async_exec(cmd)
        cls._process_logging(logger, stdout.decode(), to_stdout)
        return proc.returncode if proc.returncode is not None else 255

    @classmethod
    async def rm_networks(
        cls, logger: Logger, contains: str | list[str], to_stdout: bool = False
    ) -> int:
        network_names = await cls.get_networks(contains)
        if not network_names:
            return -1
        cmd = ["podman", "network", "rm"] + network_names
        proc, stdout = await fit_ctf_utils.create_async_exec(cmd)
        cls._process_logging(logger, stdout.decode(), to_stdout)
        return proc.returncode if proc.returncode is not None else 255

    @classmethod
    async def compose_up(
        cls, logger: Logger, file: str | Path, to_stdout: bool = False
    ) -> int:
        if isinstance(file, Path):
            file = str(file.resolve())
        cmd = f"podman-compose -f {file} up -d"
        proc, stdout = await fit_ctf_utils.create_async_exec(cmd.split())
        cls._process_logging(logger, stdout.decode(), to_stdout)
        return proc.returncode if proc.returncode is not None else 255

    @classmethod
    async def compose_down(
        cls, logger: Logger, file: str | Path, to_stdout: bool = False
    ) -> int:
        if isinstance(file, Path):
            file = str(file.resolve())
        _, stdout = await fit_ctf_utils.create_async_exec(
            ["podman-compose", "-f", file, "ps", "-q"]
        )
        if not stdout.decode().strip():
            return 0
        proc, stdout = await fit_ctf_utils.create_async_exec(
            ["podman-compose", "-f", file, "down"],
        )
        cls._process_logging(logger, stdout.decode(), to_stdout)
        return proc.returncode if proc.returncode is not None else 255

    @classmethod
    async def compose_ps(cls, file: str | Path) -> list[str]:
        if isinstance(file, Path):
            file = str(file.resolve())
        cmd = ["podman-compose", "-f", file, "ps", "--format", '"{{ .Names }}"']
        _, stdout = await fit_ctf_utils.create_async_exec(cmd)
        return [data.strip('"') for data in stdout.decode().rsplit()]

    @classmethod
    async def compose_ps_json(cls, file: str | Path) -> list[dict[str, Any]]:
        if isinstance(file, Path):
            file = str(file.resolve())
        cmd = ["podman-compose", "-f", file, "ps", "--format", "json"]
        _, stdout = await fit_ctf_utils.create_async_exec(cmd)
        data = json.loads(stdout)
        return data

    @classmethod
    async def compose_build(
        cls, logger: Logger, file: str | Path, to_stdout: bool = False
    ) -> int:
        if isinstance(file, Path):
            file = str(file.resolve())
        cmd = f"podman-compose -f {file} build"
        proc, stdout = await fit_ctf_utils.create_async_exec(cmd.split())
        cls._process_logging(logger, stdout.decode(), to_stdout)
        return proc.returncode if proc.returncode is not None else 255

    @classmethod
    def compose_shell(
        cls, file: str | Path, service: str, command: str
    ) -> subprocess.CompletedProcess:  # pragma: no cover
        if isinstance(file, Path):
            file = str(file.resolve())
        cmd = f"podman-compose -f {file} exec {service} {command}"
        return subprocess.run(cmd.split(), stdout=sys.stdout, stderr=sys.stderr)

    @classmethod
    async def stats(cls, project_name: str) -> list[dict[str, str]]:
        cmd = [
            "podman",
            "stats",
            "--no-stream",
            "--format",
            # "table {{.Name}} {{.CPUPerc}} {{.MemUsage}} {{.UpTime}}",
            "json",
        ]
        _, stdout = await fit_ctf_utils.create_async_exec(cmd)
        data = json.loads(stdout)
        return [d for d in data if d["name"].startswith(project_name)]

    @classmethod
    async def ps(cls, project_name: str) -> list[str]:
        cmd = [
            "podman",
            "ps",
            "-a",
            "--format",
            "table {{.Names}} {{.Networks}} {{.Ports}} {{.State}} {{.CreatedHuman}}",
            f"--filter=name=^{project_name}",
        ]
        _, stdout = await fit_ctf_utils.create_async_exec(cmd)
        return [data.strip('"') for data in stdout.decode().rsplit("\n") if data]

    @classmethod
    async def ps_json(cls, project_name: str) -> list[dict[str, Any]]:
        cmd = [
            "podman",
            "ps",
            "-a",
            "--format",
            "json",
            f"--filter=name=^{project_name}",
        ]
        _, stdout = await fit_ctf_utils.create_async_exec(cmd)
        data = json.loads(stdout)
        return data

    @classmethod
    async def compose_states(
        cls, file: str | Path
    ) -> list[HealthCheckDict]:  # pragma: no cover
        if isinstance(file, Path):
            file = str(file.resolve())
        _, stdout = await fit_ctf_utils.create_async_exec(
            ["podman-compose", "-f", file, "ps", "--format", "json"]
        )
        data = json.loads(stdout)
        # filtering
        return [
            {
                "name": service["Names"][0],
                "state": service["State"],
                "image": service["Image"],
            }
            for service in data
        ]

    @classmethod
    async def project_stats(cls, project_name: str) -> list[dict]:
        cmd = [
            "podman",
            "ps",
            "-a",
            "--format",
            "json",
            "--filter",
            f"label=project={project_name}",
        ]
        _, stdout = await fit_ctf_utils.create_async_exec(cmd)
        data = json.loads(stdout)
        return data
