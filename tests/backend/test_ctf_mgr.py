import pathlib
import shutil
import tempfile
import zipfile
from unittest.mock import patch

import pytest

from fit_ctf.exceptions import CTFBaseException
from fit_ctf.components.data_parser.yaml_parser import YamlParser
from fit_ctf.models.utils.exceptions import ProjectNotExistException
from tests import FixtureData, fixture_path


def _clear_db_and_share_paths(ctf_app):
    ctf_app.user_cluster_mgr.remove_docs_by_filter()
    ctf_app.project_cluster_mgr.remove_docs_by_filter()
    ctf_app.enroll_mgr.remove_docs_by_filter()
    ctf_app.user_mgr.remove_docs_by_filter()
    ctf_app.prj_mgr.remove_docs_by_filter()
    for name in ("prj1", "prj2"):
        p = ctf_app.paths.project_path(name)
        if p.exists():
            shutil.rmtree(p)
    for username in ("user1", "user2", "user3"):
        p = ctf_app.paths.user_path(username)
        if p.exists():
            shutil.rmtree(p)


def test_export_project(connected_data: FixtureData):
    ctf_app, tmp_path = connected_data
    zip_path = tmp_path / "project.zip"
    with pytest.raises(ProjectNotExistException):
        ctf_app.export_project("prj3", str(zip_path.resolve()))

    assert not zip_path.exists()
    ctf_app.export_project("prj2", str(zip_path.resolve()))
    assert zip_path.exists()

    with tempfile.TemporaryDirectory() as tmp_dir:
        with zipfile.ZipFile(zip_path, "r") as zf:
            assert "database_dump.yaml" in zf.namelist()
            zf.extractall(tmp_dir)
            data = YamlParser.load_data_file(
                pathlib.Path(tmp_dir) / "database_dump.yaml"
            )
            assert len(data["enrollments"]) == 2
            enroll_doc = [i for i in data["enrollments"] if i["user"] == "user1"][0]
            assert (
                enroll_doc
                and len(enroll_doc["progress"]["solved_secrets"]) == 1
                and enroll_doc["progress"]["last_submit_time"]
                and enroll_doc["progress"]["found_secrets"] == 1
            )
            assert set(data["modules"]) == {"ssh_ubi"}
            assert len(data["users"]) == 2
            assert data["project"]["name"] == "prj2"

            assert len(list((pathlib.Path(tmp_dir) / "user").iterdir())) == 2
            mod_path = pathlib.Path(tmp_dir) / "module"
            assert mod_path.exists() and len(list(mod_path.iterdir())) >= 1


def test_import_project(empty_data: FixtureData):
    ctf_app, tmp_path = empty_data
    # generated from the previous test case
    zip_path = tmp_path / "project.zip"
    assert not ctf_app.prj_mgr.get_docs()
    assert not ctf_app.user_mgr.get_docs()
    assert not ctf_app.enroll_mgr.get_docs()

    ctf_app.import_project(zip_path)

    assert ctf_app.prj_mgr.get_project("prj2")
    assert len(ctf_app.user_mgr.get_docs()) == 2
    assert len(ctf_app.enroll_mgr.get_docs()) == 2

    enrollment = ctf_app.enroll_mgr.get_enrollment(
        ctf_app.user_mgr.get_user("user1"), ctf_app.prj_mgr.get_project("prj2")
    )
    assert (
        enrollment
        and len(enrollment.progress.solved_secrets) == 1
        and enrollment.progress.last_submit_time
        and enrollment.progress.found_secrets == 1
    )

    # clean up here since the tmp_path is defined for the session scope
    zip_path.unlink()


def test_import_project_skips_failed_user_insert(connected_data: FixtureData):
    ctf_app, tmp_path = connected_data
    zip_path = tmp_path / "partial_user_insert.zip"
    ctf_app.export_project("prj2", str(zip_path.resolve()))

    _clear_db_and_share_paths(ctf_app)

    orig_insert = ctf_app.user_mgr.create_and_insert_doc

    def insert_fail_user1(**kw):
        if kw.get("username") == "user1":
            raise RuntimeError("simulated user insert failure")
        return orig_insert(**kw)

    with patch.object(
        ctf_app.user_mgr, "create_and_insert_doc", side_effect=insert_fail_user1
    ):
        ctf_app.import_project(zip_path)

    assert ctf_app.prj_mgr.get_project("prj2")
    assert ctf_app.user_mgr.get_doc_by_filter(username="user2")
    assert not ctf_app.user_mgr.get_doc_by_filter(username="user1")
    assert len(ctf_app.enroll_mgr.get_docs()) == 1
    ctf_app.enroll_mgr.get_enrollment(
        ctf_app.user_mgr.get_user("user2"), ctf_app.prj_mgr.get_project("prj2")
    )
    zip_path.unlink()


def test_import_project_reverts_user_on_enrollment_failure(connected_data: FixtureData):
    ctf_app, tmp_path = connected_data
    zip_path = tmp_path / "partial_enroll.zip"
    ctf_app.export_project("prj2", str(zip_path.resolve()))

    _clear_db_and_share_paths(ctf_app)

    orig_import = ctf_app.enroll_mgr.import_enrollment

    def enroll_fail_user2(user, project_name, progress, **kw):
        if user == "user2":
            raise RuntimeError("simulated enrollment failure")
        return orig_import(user, project_name, progress, **kw)

    with patch.object(
        ctf_app.enroll_mgr, "import_enrollment", side_effect=enroll_fail_user2
    ):
        ctf_app.import_project(zip_path)

    assert ctf_app.user_mgr.get_doc_by_filter(username="user1")
    assert not ctf_app.user_mgr.get_doc_by_filter(username="user2")
    assert len(ctf_app.enroll_mgr.get_docs()) == 1
    zip_path.unlink()


def test_setup_skips_user_after_creation_failure(empty_data: FixtureData):
    ctf_app, _ = empty_data
    orig = ctf_app.user_mgr.create_new_user

    def create_fail_user2(**kw):
        if kw.get("username") == "user2":
            raise RuntimeError("simulated user creation failure")
        return orig(**kw)

    with patch.object(
        ctf_app.user_mgr, "create_new_user", side_effect=create_fail_user2
    ):
        ctf_app.setup_env_from_file(fixture_path() / "user_data.yaml")

    assert ctf_app.user_mgr.get_doc_by_filter(username="user1")
    assert not ctf_app.user_mgr.get_doc_by_filter(username="user2")
    assert ctf_app.user_mgr.get_doc_by_filter(username="user3")


async def test_setup_env_from_file(empty_data: FixtureData):
    ctf_app, _ = empty_data

    ctf_app.setup_env_from_file(fixture_path() / "project_data.yaml")
    with pytest.raises(CTFBaseException):
        ctf_app.setup_env_from_file(fixture_path() / "project_data.yaml")

    ctf_app.setup_env_from_file(fixture_path() / "user_data.yaml")
    with pytest.raises(CTFBaseException):
        ctf_app.setup_env_from_file(fixture_path() / "user_data.yaml")

    await ctf_app.prj_mgr.delete_all()
    await ctf_app.user_mgr.delete_all()

    new_users = ctf_app.setup_env_from_file(fixture_path() / "connected_data.yaml")
    assert len(ctf_app.prj_mgr.get_docs()) == 2
    assert len(new_users) == 3
    assert len(ctf_app.enroll_mgr.get_docs()) == 4

    with pytest.raises(CTFBaseException):
        ctf_app.setup_env_from_file(fixture_path() / "user_data.yaml")
        ctf_app.setup_env_from_file(fixture_path() / "project_data.yaml")
    ctf_app.setup_env_from_file(fixture_path() / "user_data.yaml", exist_ok=True)
    ctf_app.setup_env_from_file(fixture_path() / "project_data.yaml", exist_ok=True)

    assert not ctf_app.setup_env_from_file(
        fixture_path() / "user_data.yaml", dry_run=True
    )
