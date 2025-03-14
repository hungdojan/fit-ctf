import csv
import re
import tempfile
from io import StringIO
from pathlib import Path

from fit_ctf_backend.cli import cli
from fit_ctf_utils.auth.local_auth import LocalAuth
from fit_ctf_utils.data_parser.yaml_parser import YamlParser
from tests import CLIData


def test_cli_create_user(cli_data: CLIData):
    ctf_mgr, _, cli_runner = cli_data

    cmd = "user create -u user1 --generate-password".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1
    assert re.search("already exists.$", result.output)

    cmd = "user create -u user4".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1

    cmd = "user create -u user4 -p test".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1
    assert re.match("Password is not strong enough.", result.output)

    cmd = "user create -u user4 -p strongPassword1 -f csv".split()
    result = cli_runner.invoke(cli, cmd)

    f = StringIO(result.output)
    data = list(csv.reader(f))[1]
    assert data[0] == "user4" and data[1] == "strongPassword1"
    assert LocalAuth(ctf_mgr.user_mgr).validate_credentials(data[0], data[1])

    cmd = "user create -u user5 --generate-password -f csv".split()
    result = cli_runner.invoke(cli, cmd)

    f = StringIO(result.output)
    data = list(csv.reader(f))[1]
    assert LocalAuth(ctf_mgr.user_mgr).validate_credentials(data[0], data[1])


def test_cli_create_multiple_users(cli_data: CLIData):
    ctf_mgr, _, cli_runner = cli_data
    with tempfile.NamedTemporaryFile("w+") as tf:
        tf.writelines("\n".join(["user3", "user4", "user5"]))
        tf.flush()

        tf.seek(0)
        assert len(ctf_mgr.user_mgr.get_docs()) == 3
        cmd = f"user create-multiple -i {str(Path(tf.name).resolve())} -f csv".split()
        result = cli_runner.invoke(cli, cmd)
        assert result.exit_code == 0
        assert len(ctf_mgr.user_mgr.get_docs()) == 5

        f = StringIO(result.output)
        for user_data in list(csv.reader(f))[1:]:
            LocalAuth(ctf_mgr.user_mgr).validate_credentials(user_data[0], user_data[1])


def test_cli_list_users(cli_data: CLIData):
    ctf_mgr, _, cli_runner = cli_data
    cmd = "user ls -f csv".split()
    result = cli_runner.invoke(cli, cmd)

    assert result.exit_code == 0

    f = StringIO(result.output)
    data = list(csv.reader(f))[1:]
    assert len(data) == 3
    for d in data:
        assert ctf_mgr.user_mgr.get_doc_by_filter(username=d[0])


def test_cli_get_user_info(cli_data: CLIData):
    ctf_mgr, _, cli_runner = cli_data
    cmd = "user get -u user4".split()
    result = cli_runner.invoke(cli, cmd)

    assert result.exit_code == 1
    assert re.search("not exist.$", result.output)

    cmd = "user get -u user1".split()
    result = cli_runner.invoke(cli, cmd)

    assert result.exit_code == 0
    f = StringIO(result.output)
    data = YamlParser.load_data_stream(f)
    user = ctf_mgr.user_mgr.get_user(data["username"])
    for key, value in data.items():
        assert getattr(user, key) == value


def test_cli_enrolled_projects(cli_data: CLIData):
    ctf_mgr, _, cli_runner = cli_data
    cmd = "user enrolled-projects -u user4"
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1
    assert re.search("not exist.$", result.output)

    user, _ = ctf_mgr.user_mgr.create_new_user("user4", "strongPassword1")
    cmd = f"user enrolled-projects -u {user.username}"
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0
    assert re.search("not enrolled", result.output)

    cmd = "user enrolled-projects -u user2 -f csv"
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0
    f = StringIO(result.output)
    data = list(csv.reader(f))[1:]
    assert (
        len(data) == 2
        and all([row[1] == "True" for row in data])
        and all(int(row[3]) == 3 for row in data)
    )


def test_cli_change_password(cli_data: CLIData):
    ctf_mgr, _, cli_runner = cli_data
    cmd = "user change-password -u user4 -p newPassword1".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1
    assert re.search("not exist.$", result.output)

    assert LocalAuth(ctf_mgr.user_mgr).validate_credentials("user2", "user2Password")
    cmd = "user change-password -u user2 -p newPassword1".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0
    assert not LocalAuth(ctf_mgr.user_mgr).validate_credentials(
        "user2", "user2Password"
    )
    assert LocalAuth(ctf_mgr.user_mgr).validate_credentials("user2", "newPassword1")


def test_cli_delete_user(cli_data: CLIData):
    ctf_mgr, _, cli_runner = cli_data
    cmd = "user delete user4".split()
    result = cli_runner.invoke(cli, cmd)
    assert len(ctf_mgr.user_mgr.get_docs()) == 3

    assert ctf_mgr.user_mgr.get_user("user2")
    cmd = "user delete user2 user3".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0
    assert not ctf_mgr.user_mgr.get_doc_by_filter(username="user2")

    cmd = "user ls -f csv".split()
    result = cli_runner.invoke(cli, cmd)

    f = StringIO(result.output)
    data = list(csv.reader(f))[1:]
    assert len(data) == 1
