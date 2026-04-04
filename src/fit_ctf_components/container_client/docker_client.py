import asyncio
import json
import pathlib
import subprocess
import sys
from pathlib import Path
from typing import Any

import fit_ctf_components.container_client.container_client_interface as c_client
from fit_ctf_components.types import ErrorCode, HealthCheckDict, TaskSuccess


class DockerClient(c_client.ContainerClientInterface):

    def generate_container_prefix(self, *names: str) -> str:
        return f"{'_'.join(names)}-"

    async def get_images(self, contains: str | list[str] | None = None) -> list[str]:
        cmd = ["docker", "images", "--format", '"{{ .Repository }}"']
        return await self._process_get_commands(cmd, contains)

    def create_network(
        self, logger_name: str, name: str, to_stdout: bool = False
    ) -> ErrorCode:
        cmd = ["docker", "network", "create", name]
        return self._run_logged_sync(cmd, logger_name, to_stdout=to_stdout)

    async def get_networks(self, contains: str | list[str] | None = None) -> list[str]:
        cmd = ["docker", "network", "ls", "--format", '"{{ .Name }}"']
        return await self._process_get_commands(cmd, contains)

    def rm_network(
        self, logger_name: str, name: str, to_stdout: bool = False
    ) -> ErrorCode:
        cmd = ["docker", "network", "rm", name]
        return self._run_logged_sync(cmd, logger_name, to_stdout=to_stdout)

    async def rm_images(
        self, logger_name: str, contains: str | list[str], to_stdout: bool = False
    ) -> ErrorCode:
        images = await self.get_images(contains)
        if not images:
            return -1
        cmd = ["docker", "rmi"] + images
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        await self._process_logging(proc, logger_name=logger_name, to_stdout=to_stdout)
        await proc.wait()
        return proc.returncode if proc.returncode is not None else 255

    async def rm_networks(
        self, logger_name: str, contains: str | list[str], to_stdout: bool = False
    ) -> ErrorCode:
        network_names = await self.get_networks(contains)
        if not network_names:
            return -1
        cmd = ["docker", "network", "rm"] + network_names
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        await self._process_logging(proc, logger_name=logger_name, to_stdout=to_stdout)
        await proc.wait()
        return proc.returncode if proc.returncode is not None else 255

    async def compose_up(
        self, logger_name: str, files: list[Path], to_stdout: bool = False
    ) -> ErrorCode:
        # TODO: eliminate whitespaces
        if not files:
            return 1
        cmd = (
            ["docker", "compose"]
            + [f"-f {str(f.resolve())}" for f in files]
            + ["up", "-d"]
        )
        cmd = " ".join(cmd)
        proc = await asyncio.create_subprocess_exec(
            *cmd.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await self._process_logging(proc, logger_name=logger_name, to_stdout=to_stdout)
        await proc.wait()
        return proc.returncode if proc.returncode is not None else 255

    async def compose_down(
        self, logger_name: str, files: list[Path], to_stdout: bool = False
    ) -> tuple[ErrorCode, TaskSuccess]:
        if not files:
            return 0, True
        file_args = [f"-f {str(f.resolve())}" for f in files]
        res = subprocess.check_output(
            ["docker", "compose"] + file_args + ["ps", "-q"], text=True
        )
        if not res.strip():
            return 0, False
        cmd = ["docker", "compose"] + file_args + ["down"]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        await self._process_logging(proc, logger_name=logger_name, to_stdout=to_stdout)
        await proc.wait()
        if proc.returncode is None:
            return 255, False
        if proc.returncode:
            return proc.returncode, False
        # return code 0 means correct clear
        return proc.returncode, not proc.returncode

    async def compose_ps(self, files: list[Path]) -> list[str]:
        if not files:
            return []
        file_args = [f"-f {str(f.resolve())}" for f in files]
        cmd = ["docker", "compose"] + file_args + ["ps", "--format", '"{{ .Names }}"']
        cmd = " ".join(cmd)
        proc = await asyncio.create_subprocess_exec(
            *cmd.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        return [data.strip('"') for data in stdout.decode().rsplit()]

    async def compose_ps_json(self, files: list[Path]) -> list[dict[str, Any]]:
        if not files:
            return []
        file_args = [f"-f {str(f.resolve())}" for f in files]
        cmd = ["docker", "compose"] + file_args + ["ps", "--format", "json"]
        cmd = " ".join(cmd)
        proc = await asyncio.create_subprocess_exec(
            *cmd.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        data = json.loads(stdout)
        return data

    async def compose_build(
        self, logger_name: str, files: list[Path], to_stdout: bool = False
    ) -> ErrorCode:
        if not files:
            return 1
        cmd = (
            ["docker", "compose"]
            + [f"-f {str(f.resolve())}" for f in files]
            + ["build"]
        )
        cmd = " ".join(cmd)
        proc = await asyncio.create_subprocess_exec(
            *cmd.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await self._process_logging(proc, logger_name=logger_name, to_stdout=to_stdout)
        await proc.wait()
        return proc.returncode if proc.returncode is not None else 255

    async def compose_logs(
        self,
        logger_name: str,
        files: list[Path],
        *,
        tail: int = 500,
        service: str | None = None,
        to_stdout: bool = True,
    ) -> ErrorCode:
        if not files:
            return 1
        parts = (
            ["docker", "compose"]
            + [f"-f {str(f.resolve())}" for f in files]
            + ["logs", "--no-color", f"--tail={tail}"]
        )
        if service:
            parts.append(service)
        cmd = " ".join(parts)
        proc = await asyncio.create_subprocess_exec(
            *cmd.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await self._process_logging(proc, logger_name=logger_name, to_stdout=to_stdout)
        await proc.wait()
        return proc.returncode if proc.returncode is not None else 255

    def compose_shell(
        self, files: list[Path], service: str, command: str
    ) -> subprocess.CompletedProcess:  # pragma: no cover
        if not files:
            raise ValueError()
        cmd = (
            ["docker", "compose"]
            + [f"-f {str(f.resolve())}" for f in files]
            + ["exec", service, command]
        )
        cmd = " ".join(cmd)
        return subprocess.run(cmd.split(), stdout=sys.stdout, stderr=sys.stderr)

    async def stats(self, project_name: str) -> list[dict[str, str]]:
        cmd = [
            "docker",
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
            "docker",
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
            "docker",
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

    async def ps_csv(self, project_name: str, output_file: pathlib.Path):
        cmd = [
            "docker",
            "ps",
            "-a",
            "--no-truc" "--format",
            'table "{{.Names}}","{{.Networks}}","{{.Ports}}","{{.State}}","{{.CreatedHuman}}"',
            f"--filter=name=^{project_name}",
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
        )
        stdout, _ = await proc.communicate()
        # TODO: print to file
        print([data.strip('"') for data in stdout.decode().rsplit("\n") if data])

    async def compose_states(
        self, files: list[Path]
    ) -> list[HealthCheckDict]:  # pragma: no cover
        file_args = [f"-f {str(f.resolve())}" for f in files]
        cmd = ["docker", "compose"] + file_args + ["ps", "--format", "json"]
        cmd = " ".join(cmd)
        proc = await asyncio.create_subprocess_exec(
            *cmd.split(),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
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
            "docker",
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

    async def build_image(
        self,
        logger_name: str,
        context_path: Path,
        image_name: str,
        containerfile: str = "Containerfile",
        to_stdout: bool = False,
    ) -> ErrorCode:
        """Build a container image from a Containerfile/Dockerfile.

        :param logger_name: Logger name for output
        :type logger_name: str
        :param context_path: Path to build context directory
        :type context_path: Path
        :param image_name: Name to tag the built image
        :type image_name: str
        :param containerfile: Name of Containerfile/Dockerfile (default: "Containerfile")
        :type containerfile: str
        :param to_stdout: Pipe output to stdout as well
        :type to_stdout: bool
        :return: An exit code
        :rtype: ErrorCode
        """
        cmd = [
            "docker",
            "build",
            "-t",
            image_name,
            "-f",
            str(context_path / containerfile),
            str(context_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await self._process_logging(proc, logger_name=logger_name, to_stdout=to_stdout)
        await proc.wait()
        return proc.returncode if proc.returncode is not None else 255
