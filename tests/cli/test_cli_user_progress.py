import csv
from io import StringIO

from fit_ctf.cli import cli
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
    assert len(rows[1:]) == len(
        ctf_app.enroll_mgr.get_enrollment(
            ctf_app.user_mgr.get_user("user1"), ctf_app.prj_mgr.get_project("prj2")
        ).progress.list_secrets()
    )


def test_add_secret(cli_data: CLIData):
    ctf_app, _, cli_runner = cli_data

    # missing required values
    cmd = "user-progress -pn prj2 -u user1 add-secret".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    # already existing name
    cmd = "user-progress -pn prj2 -u user1 add-secret -n key1 -v new-secret".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    # already existing secret value
    cmd = "user-progress -pn prj2 -u user1 add-secret -n new-key -v value1".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    # correct
    cmd = "user-progress -pn prj2 -u user1 add-secret -n new-key -v new-secret".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0
    assert (
        len(
            ctf_app.enroll_mgr.get_enrollment(
                ctf_app.user_mgr.get_user("user1"), ctf_app.prj_mgr.get_project("prj2")
            ).progress.list_secrets()
        )
        == 3
    )


def test_update_secret(cli_data: CLIData):
    ctf_app, _, cli_runner = cli_data

    # missing required values
    cmd = "user-progress -pn prj2 -u user1 update-secret".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    # unknown secret name
    cmd = "user-progress -pn prj2 -u user1 update-secret -n key3 -v new-secret".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    # already existing secret value
    cmd = "user-progress -pn prj2 -u user1 update-secret -n key2 -v value1".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    user = ctf_app.user_mgr.get_user("user1")
    project = ctf_app.prj_mgr.get_project("prj2")
    # correct
    cmd = "user-progress -pn prj2 -u user1 update-secret -n key2 -v new-secret".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0
    assert ctf_app.enroll_mgr.get_enrollment(
        ctf_app.user_mgr.get_user("user1"), ctf_app.prj_mgr.get_project("prj2")
    ).progress.get_secret_by_value("new-secret")

    assert ctf_app.enroll_mgr.get_enrollment(user, project).progress.found_secrets == 1
    cmd = "user-progress -pn prj2 -u user1 update-secret -n key1 -v another-secret -r".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0
    assert ctf_app.enroll_mgr.get_enrollment(user, project).progress.found_secrets == 0


def test_delete_secret(cli_data: CLIData):
    ctf_app, _, cli_runner = cli_data
    user = ctf_app.user_mgr.get_user("user1")
    project = ctf_app.prj_mgr.get_project("prj2")

    # missing required values
    cmd = "user-progress -pn prj2 -u user1 delete-secret".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    # unknown secret name
    cmd = "user-progress -pn prj2 -u user1 delete-secret -n key3".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    # correct
    cmd = "user-progress -pn prj2 -u user1 delete-secret -n key2".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0
    progress = ctf_app.enroll_mgr.get_enrollment(user, project).progress
    assert progress.found_secrets == 1 and len(progress.list_secrets()) == 1

    # the secret does not exist anymore
    cmd = "user-progress -pn prj2 -u user1 delete-secret -n key2".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    # correct
    cmd = "user-progress -pn prj2 -u user1 delete-secret -n key1".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0
    progress = ctf_app.enroll_mgr.get_enrollment(user, project).progress
    assert progress.found_secrets == 0 and not progress.list_secrets()


def test_submit_secret(cli_data: CLIData):
    ctf_app, _, cli_runner = cli_data
    user = ctf_app.user_mgr.get_user("user1")
    project = ctf_app.prj_mgr.get_project("prj2")

    # missing required values
    cmd = "user-progress -pn prj2 -u user1 submit-secret".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    # secret not found
    cmd = "user-progress -pn prj2 -u user1 submit-secret -v invalid-value".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0 and result.output.strip() == "Secret is incorrect."

    # secret already submitted
    cmd = "user-progress -pn prj2 -u user1 submit-secret -v value1".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    # correct
    cmd = "user-progress -pn prj2 -u user1 submit-secret -v value2".split()
    result = cli_runner.invoke(cli, cmd)
    assert (
        result.exit_code == 0
        and result.output.strip() == "Secret was successfully submitted."
    )
    progress = ctf_app.enroll_mgr.get_enrollment(user, project).progress
    assert progress.found_secrets == 2

    # secret already submitted
    cmd = "user-progress -pn prj2 -u user1 submit-secret -v value2".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0


def test_progress_info(cli_data: CLIData):
    ctf_app, _, cli_runner = cli_data
    user = ctf_app.user_mgr.get_user("user1")
    project = ctf_app.prj_mgr.get_project("prj2")
    enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

    # missing required values
    cmd = "user-progress info".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    # user not found
    cmd = "user-progress -pn prj2 -u unknownUser info".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code != 0

    # secret not found
    cmd = f"user-progress -pn prj2 -u {user.username} info --format csv".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0

    f = StringIO(result.output)
    data = list(csv.DictReader(f))
    assert data
    info = data[0]
    assert info["User"] == user.username
    assert int(info["Found"]) == enrollment.progress.found_secrets
    assert int(info["Total"]) == len(enrollment.progress.list_secrets())
    assert "Last Found" in info
