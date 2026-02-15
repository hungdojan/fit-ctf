import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import fit_ctf_components.container_client.container_client_interface as c_client
from fit_ctf_components.types import ErrorCode, HealthCheckDict, TaskSuccess


class PodmanClient(c_client.ContainerClientInterface):

    def generate_container_prefix(self, *names: str) -> str:
        return f"{'_'.join(names)}_"

    async def get_images(self, contains: str | list[str] | None = None) -> list[str]:
        cmd = ["podman", "images", "--format", '"{{ .Repository }}"']
        return await self._process_get_commands(cmd, contains)

    async def get_networks(self, contains: str | list[str] | None = None) -> list[str]:
        cmd = ["podman", "network", "ls", "--format", '"{{.Name}}"']
        return await self._process_get_commands(cmd, contains)

    async def rm_images(
        self, logger_name: str, contains: str | list[str], to_stdout: bool = False
    ) -> int:
        images = await self.get_images(contains)
        if not images:
            return -1
        cmd = ["podman", "rmi"] + images
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        await self._process_logging(proc, logger_name=logger_name, to_stdout=to_stdout)
        await proc.wait()
        return proc.returncode if proc.returncode is not None else 255

    async def rm_networks(
        self, logger_name: str, contains: str | list[str], to_stdout: bool = False
    ) -> int:
        network_names = await self.get_networks(contains)
        if not network_names:
            return -1
        cmd = ["podman", "network", "rm"] + network_names
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        await self._process_logging(proc, logger_name=logger_name, to_stdout=to_stdout)
        return proc.returncode if proc.returncode is not None else 255

    async def compose_up(
        self, logger_name: str, file: str | Path, to_stdout: bool = False
    ) -> int:
        if isinstance(file, Path):
            file = str(file.resolve())
        cmd = f"podman-compose -f {file} up -d"
        proc = await asyncio.create_subprocess_exec(
            *cmd.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await self._process_logging(proc, logger_name=logger_name, to_stdout=to_stdout)

        await proc.wait()
        return proc.returncode if proc.returncode is not None else 255

    async def compose_down(
        self, logger_name: str, file: str | Path, to_stdout: bool = False
    ) -> tuple[ErrorCode, TaskSuccess]:
        if isinstance(file, Path):
            file = str(file.resolve())
        cmd = ["podman-compose", "-f", file, "ps", "-q"]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await proc.communicate()
        if not stdout.decode().strip():
            return 0, False
        cmd = ["podman-compose", "-f", file, "down"]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        await self._process_logging(proc, logger_name=logger_name, to_stdout=to_stdout)
        await proc.wait()
        if proc.returncode is None:
            return 255, False
        if proc.returncode:
            return proc.returncode, False
        # return code 0 means correct clear
        return proc.returncode, not proc.returncode

    async def compose_ps(self, file: str | Path) -> list[str]:
        if isinstance(file, Path):
            file = str(file.resolve())
        cmd = ["podman-compose", "-f", file, "ps", "--format", '"{{ .Names }}"']
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await proc.communicate()
        return [data.strip('"') for data in stdout.decode().rsplit()]

    async def compose_ps_json(self, file: str | Path) -> list[dict[str, Any]]:
        if isinstance(file, Path):
            file = str(file.resolve())
        cmd = ["podman-compose", "-f", file, "ps", "--format", "json"]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout)
        return data

    async def compose_build(
        self, logger_name: str, file: str | Path, to_stdout: bool = False
    ) -> int:
        if isinstance(file, Path):
            file = str(file.resolve())
        cmd = f"podman-compose -f {file} build"
        proc = await asyncio.create_subprocess_exec(
            *cmd.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await self._process_logging(proc, logger_name=logger_name, to_stdout=to_stdout)
        await proc.wait()
        return proc.returncode if proc.returncode is not None else 255

    def compose_shell(
        self, file: str | Path, service: str, command: str
    ) -> subprocess.CompletedProcess:  # pragma: no cover
        if isinstance(file, Path):
            file = str(file.resolve())
        cmd = f"podman-compose -f {file} exec {service} {command}"
        return subprocess.run(cmd.split(), stdout=sys.stdout, stderr=sys.stderr)

    async def stats(self, project_name: str) -> list[dict[str, str]]:
        cmd = [
            "podman",
            "stats",
            "--no-stream",
            "--format",
            # "table {{.Name}} {{.CPUPerc}} {{.MemUsage}} {{.UpTime}}",
            "json",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout)
        return [d for d in data if d["name"].startswith(project_name)]

    async def ps(self, project_name: str) -> list[str]:
        cmd = [
            "podman",
            "ps",
            "-a",
            "--format",
            "table {{.Names}} {{.Networks}} {{.Ports}} {{.State}} {{.CreatedHuman}}",
            f"--filter=name=^{project_name}",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await proc.communicate()
        return [data.strip('"') for data in stdout.decode().rsplit("\n") if data]

    async def ps_json(self, project_name: str) -> list[dict[str, Any]]:
        cmd = [
            "podman",
            "ps",
            "-a",
            "--format",
            "json",
            f"--filter=name=^{project_name}",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout)
        return data

    async def ps_csv(self, project_name: str, output_file: Path) -> None:
        # TODO: implement
        pass

    async def compose_states(
        self, file: str | Path
    ) -> list[HealthCheckDict]:  # pragma: no cover
        if isinstance(file, Path):
            file = str(file.resolve())
        cmd = ["podman-compose", "-f", file, "ps", "--format", "json"]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await proc.communicate()
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

    async def project_stats(self, project_name: str) -> list[dict]:
        cmd = [
            "podman",
            "ps",
            "-a",
            "--format",
            "json",
            "--filter",
            f"label=project={project_name}",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout)
        return data
