import re
import tempfile
from pathlib import Path

from fit_ctf_backend.cli import cli
from tests import CLIData, fixture_path


def test_cli_enroll_user(cli_data: CLIData):
    ctf_mgr, _, cli_runner = cli_data
    cmd = "enrollment enroll -u user1 -pn new_prj".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1
    assert re.search("not exist.$", result.output)

    cmd = "enrollment enroll -u new_user -pn prj1".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1
    assert re.search("not exist.$", result.output)

    cmd = "enrollment enroll -u user2 -pn prj1".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1
    assert re.search("already enrolled", result.output)

    assert (
        len(ctf_mgr.user_enrollment_mgr.get_user_enrollments_for_project("prj1")) == 2
    )
    cmd = "enrollment enroll -u user1 -pn prj1".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0
    assert re.search("was enrolled", result.output)
    assert (
        len(ctf_mgr.user_enrollment_mgr.get_user_enrollments_for_project("prj1")) == 3
    )


def test_cli_enroll_multiple_users(empty_cli_data: CLIData):
    ctf_mgr, _, cli_runner = empty_cli_data
    ctf_mgr.setup_env_from_file(fixture_path() / "unconnected_data.yaml")
    assert not ctf_mgr.user_enrollment_mgr.get_user_enrollments_for_project("prj1")
    with tempfile.NamedTemporaryFile("w+") as tf:
        path = Path(tf.name)
        tf.write("\n".join([f"user{i+2}" for i in range(3)]))
        tf.flush()
        tf.seek(0)

        cmd = f"enrollment enroll-multiple -pn prj1 -i {str(path.resolve())}".split()
        result = cli_runner.invoke(cli, cmd)
        assert result.exit_code == 0
        assert (
            len(ctf_mgr.user_enrollment_mgr.get_user_enrollments_for_project("prj1"))
            == 2
        )


def test_cli_cancel_enrollment(cli_data: CLIData):
    ctf_mgr, _, cli_runner = cli_data
    assert (
        len(ctf_mgr.user_enrollment_mgr.get_user_enrollments_for_project("prj1")) == 2
    )

    cmd = "enrollment cancel -u user1 -pn prj1".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1
    assert re.search("not enrolled", result.output)

    cmd = "enrollment cancel -u user2 -pn prj1".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0
    assert (
        len(ctf_mgr.user_enrollment_mgr.get_user_enrollments_for_project("prj1")) == 1
    )


def test_cli_cancel_multiple_enrollments(cli_data: CLIData):
    ctf_mgr, _, cli_runner = cli_data
    assert (
        len(ctf_mgr.user_enrollment_mgr.get_user_enrollments_for_project("prj1")) == 2
    )

    with tempfile.NamedTemporaryFile("w+") as tf:
        path = Path(tf.name)
        tf.write("\n".join([f"user{i+2}" for i in range(3)]))
        tf.flush()
        tf.seek(0)

        cmd = f"enrollment cancel-multiple -pn prj1 -i {str(path.resolve())}".split()
        result = cli_runner.invoke(cli, cmd)
        assert result.exit_code == 0
        assert not ctf_mgr.user_enrollment_mgr.get_user_enrollments_for_project("prj1")


def test_cli_cancel_user(cli_data: CLIData):
    ctf_mgr, _, cli_runner = cli_data
    assert len(ctf_mgr.user_enrollment_mgr.get_enrolled_projects("user2")) == 2

    cmd = "enrollment cancel-user -u new_user".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1
    assert re.search("not exist.$", result.output)

    cmd = "enrollment cancel-user -u user2".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0
    assert len(ctf_mgr.user_enrollment_mgr.get_enrolled_projects("user2")) == 0


def test_cli_cancel_project(cli_data: CLIData):
    ctf_mgr, _, cli_runner = cli_data
    assert (
        len(ctf_mgr.user_enrollment_mgr.get_user_enrollments_for_project("prj1")) == 2
    )

    cmd = "enrollment cancel-project -pn new_prj".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 1
    assert re.search("not exist.$", result.output)

    cmd = "enrollment cancel-project -pn prj1".split()
    result = cli_runner.invoke(cli, cmd)
    assert result.exit_code == 0
    assert (
        len(ctf_mgr.user_enrollment_mgr.get_user_enrollments_for_project("prj1")) == 0
    )
