import asyncio
import csv
import re
from io import StringIO

from fit_ctf_cli.cli import cli
from fit_ctf.components.data_parser.yaml_parser import YamlParser
from tests import CLIData


def test_create(cli_data: CLIData):
    ctf_app, _, cli_runner = cli_data
    assert len(ctf_app.prj_mgr.get_docs()) == 2

    cmd = ["project", "create", "-pn", "new_prj", "-mu", 10, "-p", 10100]
    result = cli_runner.invoke(cli, cmd)

    assert result.exit_code == 0
    assert len(ctf_app.prj_mgr.get_docs()) == 3
    assert ctf_app.prj_mgr.get_project("new_prj")

    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1


def test_list(cli_data: CLIData):
    ctf_app, _, cli_runner = cli_data
    cmd = "project ls -f csv".split()
    result = cli_runner.invoke(cli, cmd)

    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    assert len(rows[1:]) == len(ctf_app.prj_mgr.get_docs())

    for prj in ctf_app.prj_mgr.get_docs():
        asyncio.run(ctf_app.prj_mgr.disable_project(prj))

    result = cli_runner.invoke(cli, cmd)
    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    assert len(rows[1:]) == 0

    cmd = "project ls -a -f csv".split()
    result = cli_runner.invoke(cli, cmd)

    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    assert len(rows[1:]) == len(ctf_app.prj_mgr.get_docs())

    for prj in ctf_app.prj_mgr.get_docs():
        asyncio.run(ctf_app.prj_mgr.disable_project(prj))


def test_get_info(cli_data: CLIData):
    _, _, cli_runner = cli_data
    cmd = "project get-info -pn prj1".split()
    result = cli_runner.invoke(cli, cmd)

    f = StringIO(result.output)
    data = YamlParser.load_data_stream(f)
    assert data["name"] == "prj1"
    assert data["active"]

    cmd = "project get-info -pn prj10".split()
    result = cli_runner.invoke(cli, cmd)
    assert re.search("not found.$", result.output)


def test_enrolled_users(cli_data: CLIData):
    ctf_app, _, cli_runner = cli_data
    cmd = "project enrolled-users -pn prj1 -f csv".split()
    result = cli_runner.invoke(cli, cmd)

    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    assert len(rows[1:]) == len(ctf_app.enroll_mgr.get_enrollments_for_project("prj1"))

    cmd = "project enrolled-users -pn prj10 -f csv".split()
    result = cli_runner.invoke(cli, cmd)
    assert re.search("not exist.$", result.output)

    asyncio.run(ctf_app.user_mgr.disable_multiple_users(["user2", "user3"]))

    cmd = "project enrolled-users -pn prj1 -f csv".split()
    result = cli_runner.invoke(cli, cmd)
    assert re.match("No active users found.", result.output)

    cmd = "project enrolled-users -pn prj1 -f csv -a".split()
    result = cli_runner.invoke(cli, cmd)
    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    assert len(rows[1:]) == 2


def test_firewall_rules(cli_data: CLIData):
    _, tmp_path, cli_runner = cli_data
    path = tmp_path / "firewall.sh"
    assert not path.exists()
    cmd = f"project generate-firewall-rules -ip 127.0.0.1 -pn prj1 -o {str(path.resolve())}".split()
    result = cli_runner.invoke(cli, cmd)

    assert result.exit_code == 0
    assert (tmp_path / "firewall.sh").exists()


def test_used_ports(cli_data: CLIData):
    ctf_app, _, cli_runner = cli_data
    cmd = "project reserved-ports -f csv".split()
    result = cli_runner.invoke(cli, cmd)

    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    header = rows[0]
    values = rows[1:]
    for row in values:
        prj = ctf_app.prj_mgr.get_project(row[header.index("Name")])
        assert row[header.index("Min Port")] == str(prj.starting_port_bind)
        assert row[header.index("Max Port")] == str(
            prj.starting_port_bind + prj.max_nof_users - 1
        )

    asyncio.run(ctf_app.prj_mgr.delete_all())

    cmd = "project reserved-ports -f csv".split()
    result = cli_runner.invoke(cli, cmd)
    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    assert len(rows[1:]) == 0


def test_leaderboard(cli_data: CLIData):
    _, _, cli_runner = cli_data

    # missing arguments
    cmd = "project leaderboard".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    # missing
    cmd = "project leaderboard -pn prj1 --format csv".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0
    f = StringIO(result.output)
    data = list(csv.DictReader(f))
    assert len(data) == 2 and not any([i["Last submit"] for i in data])

    # missing
    cmd = "project leaderboard -pn prj2 --format csv".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0
    f = StringIO(result.output)
    data = list(csv.DictReader(f))
    assert len(data) == 2 and data[0]["User"] == "user1" and data[0]["Last submit"]


def test_delete(cli_data: CLIData):
    ctf_app, _, cli_runner = cli_data
    assert len(ctf_app.prj_mgr.get_docs()) == 2
    assert (ctf_app.paths.project_global / "prj1").is_dir()

    cmd = "project delete -pn prj1".split()
    result = cli_runner.invoke(cli, cmd)

    assert re.search("deleted successfully.$", result.output)
    assert len(ctf_app.prj_mgr.get_docs()) == 1
    assert not (ctf_app.paths.project_global / "prj1").is_dir()
