import asyncio
import csv
import re
from io import StringIO
from pathlib import Path

from fit_ctf.cli import cli
from tests import CLIData


def test_cli_create_module(cli_data: CLIData):
    ctf_app, _, cli_runner = cli_data
    cmd = "module ls -f csv".split()
    result = cli_runner.invoke(cli, cmd)

    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    assert len(rows[1:]) == 3

    cmd = "module create -mn template"
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1
    assert re.search("already exists.$", result.output)

    path = ctf_app.paths.module_global / "new_module"
    assert not path.is_dir()
    cmd = "module create -mn new_module"
    result = cli_runner.invoke(cli, cmd)

    assert re.search("successfully created.$", result.output)
    assert path.is_dir()

    cmd = "module ls -f csv".split()
    result = cli_runner.invoke(cli, cmd)
    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    assert len(rows[1:]) == 4


def test_cli_get_module_path(cli_data: CLIData):
    ctf_app, _, cli_runner = cli_data
    cmd = "module get-path -mn other_module".split()
    result = cli_runner.invoke(cli, cmd)

    assert re.match("Cannot locate", result.output)
    assert result.exit_code == 1

    path = ctf_app.paths.module_global / "template"
    cmd = "module get-path -mn template".split()
    result = cli_runner.invoke(cli, cmd)

    assert Path(result.output.strip()).is_dir()
    assert str(path.resolve()) == result.output.strip()


def test_cli_referenced(cli_data: CLIData):
    """Counts come from compiled scenario_compose.yaml (see module_mgr.reference_count)."""
    _, _, cli_runner = cli_data
    cmd = "module referenced -f csv".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0

    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    data = {row[0]: row[1] for row in rows[1:]}
    assert data == {"ssh_ubi": "4", "template": "1"}

    cmd = "module referenced -pn prj1 -f csv".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0

    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    data = {row[0]: row[1] for row in rows[1:]}
    assert data == {"ssh_ubi": "2", "template": "1"}


def test_cli_remove_module(cli_data: CLIData):
    """Sync test: ``module rm`` uses ``asyncio.run()`` and cannot run under pytest-asyncio's loop."""
    ctf_app, _, cli_runner = cli_data
    cmd = "module ls -f csv".split()
    result = cli_runner.invoke(cli, cmd)

    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    # NOTE: a new module is created in the previous tests
    assert len(rows[1:]) == 3

    cmd = "module rm -mn other-module".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1
    assert re.match("Cannot locate", result.output)

    for prj in list(ctf_app.prj_mgr.get_docs()):
        asyncio.run(ctf_app.prj_mgr.delete_project(prj))

    cmd = "module rm -mn template".split()
    result = cli_runner.invoke(cli, cmd)
    assert re.search("successfully removed.$", result.output)

    assert not (ctf_app.paths.module_global / "template").is_dir()
    #
    # cmd = "module rm -mn new_module".split()
    # result = cli_runner.invoke(cli, cmd)
    # assert re.search("successfully removed.$", result.output)
