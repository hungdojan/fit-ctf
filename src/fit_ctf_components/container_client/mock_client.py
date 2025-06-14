import subprocess
from pathlib import Path
from typing import Any

import fit_ctf_components.container_client.container_client_interface as c_client
from fit_ctf_components.types import HealthCheckDict


class MockClient(c_client.ContainerClientInterface):

    def generate_container_prefix(self, *names: str) -> str:
        return ""

    async def get_images(
        self, contains: str | list[str] | None = None
    ) -> list[str]:  # pragma: no cover
        return []

    async def get_networks(
        self, contains: str | list[str] | None = None
    ) -> list[str]:  # pragma: no cover
        return []

    async def rm_images(
        self, logger_name: str, contains: str | list[str], to_stdout: bool = False
    ) -> int:  # pragma: no cover
        return 0

    async def rm_networks(
        self, logger_name: str, contains: str | list[str], to_stdout: bool = False
    ) -> int:  # pragma: no cover
        return 0

    async def compose_up(
        self, logger_name: str, file: str | Path, to_stdout: bool = False
    ) -> int:  # pragma: no cover
        return 0

    async def compose_down(
        self, logger_name: str, file: str | Path, to_stdout: bool = False
    ) -> int:  # pragma: no cover
        return 0

    async def compose_ps(self, file: str | Path) -> list[str]:  # pragma: no cover
        return []

    async def compose_ps_json(
        self, file: str | Path
    ) -> list[dict[str, Any]]:  # pragma: no cover
        return []

    async def compose_build(
        self, logger_name: str, file: str | Path, to_stdout: bool = False
    ) -> int:  # pragma: no cover
        return 0

    def compose_shell(
        self, file: str | Path, service: str, command: str
    ) -> subprocess.CompletedProcess:  # pragma: no cover
        return subprocess.CompletedProcess(
            args=["compose", "exec", "bash"], returncode=0
        )

    async def stats(
        self, project_name: str
    ) -> list[dict[str, str]]:  # pragma: no cover
        return []

    async def ps(self, project_name: str) -> list[str]:  # pragma: no cover
        return []

    async def ps_json(
        self, project_name: str
    ) -> list[dict[str, Any]]:  # pragma: no cover
        return []

    async def ps_csv(self, project_name: str, output_file: Path):
        return

    async def project_stats(self, project_name: str) -> list[dict]:  # pragma: no cover
        return []

    async def compose_states(self, file: str | Path) -> list[HealthCheckDict]:
        return []
