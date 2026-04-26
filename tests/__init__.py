import pathlib
from typing import TYPE_CHECKING, TypeAlias

from click.testing import CliRunner

if TYPE_CHECKING:
    import fit_ctf.ctf_app as ctf_app
    import fit_ctf_rendezvous.rendezvous_app as rendezvous

FixtureData: TypeAlias = tuple["ctf_app.CTFApp", pathlib.Path]
CLIData: TypeAlias = tuple["ctf_app.CTFApp", pathlib.Path, CliRunner]
ComplexData: TypeAlias = tuple[CliRunner, "rendezvous.RendezvousApp", pathlib.Path]


def fixture_path() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "fixtures"


__all__ = ["FixtureData", "CLIData", "ComplexData", "fixture_path"]
