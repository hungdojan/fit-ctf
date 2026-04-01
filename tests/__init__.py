import pathlib
from typing import TypeAlias

from click.testing import CliRunner

import fit_ctf.ctf_app as ctf_app

FixtureData: TypeAlias = tuple["ctf_app.CTFApp", pathlib.Path]
CLIData: TypeAlias = tuple["ctf_app.CTFApp", pathlib.Path, CliRunner]


def fixture_path() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "fixtures"


__all__ = ["FixtureData", "fixture_path"]
