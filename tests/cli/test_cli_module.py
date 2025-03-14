import csv
import re
from io import StringIO
from pathlib import Path

from fit_ctf_backend.cli import cli
from tests import CLIData


def test_cli_create_module(cli_data: CLIData):
    ctf_mgr, _, cli_runner = cli_data
    cmd = "module ls -f csv".split()
    result = cli_runner.invoke(cli, cmd)

    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    assert len(rows[1:]) == 2

    cmd = "module create -mn base"
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1
    assert re.search("already exists.$", result.output)

    path = ctf_mgr._paths["modules"] / "new_module"
    assert not path.is_dir()
    cmd = "module create -mn new_module"
    result = cli_runner.invoke(cli, cmd)

    assert re.search("successfully created.$", result.output)
    assert path.is_dir()

    cmd = "module ls -f csv".split()
    result = cli_runner.invoke(cli, cmd)
    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    assert len(rows[1:]) == 3


def test_cli_get_module_path(cli_data: CLIData):
    ctf_mgr, _, cli_runner = cli_data
    cmd = "module get-path -mn other_module".split()
    result = cli_runner.invoke(cli, cmd)

    assert re.match("Cannot locate", result.output)
    assert result.exit_code == 1

    path = ctf_mgr._paths["modules"] / "base"
    cmd = "module get-path -mn base".split()
    result = cli_runner.invoke(cli, cmd)

    assert Path(result.output.strip()).is_dir()
    assert str(path.resolve()) == result.output.strip()


def test_cli_referenced(cli_data: CLIData):
    _, _, cli_runner = cli_data
    cmd = "module referenced -f csv".split()
    result = cli_runner.invoke(cli, cmd)

    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    data = {row[0]: row[1] for row in rows[1:]}
    assert data["base"] == "2"
    assert data["base_ssh"] == "4"

    cmd = "module referenced -pn prj1 -f csv".split()
    result = cli_runner.invoke(cli, cmd)

    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    data = {row[0]: row[1] for row in rows[1:]}
    assert data["base"] == "1"
    assert data["base_ssh"] == "2"


def test_cli_remove_module(cli_data: CLIData):
    ctf_mgr, _, cli_runner = cli_data
    cmd = "module ls -f csv".split()
    result = cli_runner.invoke(cli, cmd)

    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    assert len(rows[1:]) == 3

    cmd = "module rm -mn other-module".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1
    assert re.match("Cannot locate", result.output)

    cmd = "module rm -mn base".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1
    assert re.search("still used by some services.$", result.output)

    ctf_mgr.prj_mgr.delete_all()

    cmd = "module rm -mn base".split()
    result = cli_runner.invoke(cli, cmd)
    assert re.search("successfully removed.$", result.output)

    assert not (ctf_mgr._paths["modules"] / "base").is_dir()

    cmd = "module rm -mn new_module".split()
    result = cli_runner.invoke(cli, cmd)
    assert re.search("successfully removed.$", result.output)
