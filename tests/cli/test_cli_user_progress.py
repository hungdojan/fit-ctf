import csv
from io import StringIO

from fit_ctf_cli.cli import cli
from tests import CLIData


def test_help(cli_data: CLIData):
    _, _, cli_runner = cli_data
    cmd = "user-progress --help".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0


def test_list_secrets(cli_data: CLIData):
    ctf_app, _, cli_runner = cli_data
    cmd = "user-progress -pn prj2 -u user1 list-secrets --format csv".split()
    result = cli_runner.invoke(cli, cmd)

    assert result.exit_code == 0
    f = StringIO(result.output)
    rows = [i for i in csv.reader(f)]
    enrollment = ctf_app.enroll_mgr.get_enrollment(
        ctf_app.user_mgr.get_user("user1"), ctf_app.prj_mgr.get_project("prj2")
    )
    assert len(rows[1:]) == len(ctf_app.enroll_mgr.list_secrets_for_display(enrollment))


def test_submit_secret(cli_data: CLIData):
    ctf_app, _, cli_runner = cli_data
    user = ctf_app.user_mgr.get_user("user1")
    project = ctf_app.prj_mgr.get_project("prj2")

    cmd = "user-progress -pn prj2 -u user1 submit-secret".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    cmd = "user-progress -pn prj2 -u user1 submit-secret -v invalid-value".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0 and result.output.strip() == "Secret is incorrect."

    cmd = "user-progress -pn prj2 -u user1 submit-secret -v value1".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    cmd = "user-progress -pn prj2 -u user1 submit-secret -v value2".split()
    result = cli_runner.invoke(cli, cmd)
    assert (
        result.exit_code == 0
        and result.output.strip() == "Secret was successfully submitted."
    )
    progress = ctf_app.enroll_mgr.get_enrollment(user, project).progress
    assert progress.found_secrets == 2

    cmd = "user-progress -pn prj2 -u user1 submit-secret -v value2".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0


def test_progress_info(cli_data: CLIData):
    ctf_app, _, cli_runner = cli_data
    user = ctf_app.user_mgr.get_user("user1")
    project = ctf_app.prj_mgr.get_project("prj2")
    enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

    cmd = "user-progress info".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    cmd = "user-progress -pn prj2 -u unknownUser info".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    cmd = f"user-progress -pn prj2 -u {user.username} info --format csv".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0

    f = StringIO(result.output)
    data = list(csv.DictReader(f))
    assert data
    info = data[0]
    assert info["User"] == user.username
    assert int(info["Found"]) == enrollment.progress.found_secrets
    assert int(info["Total"]) == ctf_app.enroll_mgr.count_submittable_slots(enrollment)
    assert "Last Found" in info
