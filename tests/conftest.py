import os
import shutil
from pathlib import Path
from typing import Generator

import pymongo
import pymongo.errors
import pytest
from _pytest.fixtures import FixtureRequest
from click.testing import CliRunner
from dotenv import load_dotenv
from textual.app import App

from fit_ctf.components.constants import get_env_info
from fit_ctf.components.data_parser.yaml_parser import YamlParser
from fit_ctf.components.types import PathDict
from fit_ctf.ctf_app import CTFApp
from fit_ctf.utils import CTFUtils
from fit_ctf_rendezvous import i18n as rendezvous_i18n
from fit_ctf_rendezvous.rendezvous_app import RendezvousApp

from . import CLIData, ComplexData, FixtureData, fixture_path

load_dotenv()


def _base_path_dict(tmp_path: Path) -> dict:
    return {
        "PROJECT_SHARE_DIR": str((tmp_path / "share" / "project").resolve()),
        "USER_SHARE_DIR": str((tmp_path / "share" / "user").resolve()),
        "MODULE_SHARE_DIR": str((tmp_path / "share" / "module").resolve()),
        "SCENARIO_SHARE_DIR": str((tmp_path / "share" / "scenario").resolve()),
    }


@pytest.fixture(scope="session")
def workdir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return tmp_path_factory.getbasetemp()


@pytest.fixture(scope="session")
def shared_mongo_client() -> Generator[pymongo.MongoClient, None, None]:
    """Create a shared MongoDB client for all tests in the session."""
    env_info = get_env_info()
    try:
        client = CTFUtils.create_mongo_client(env_info)
    except pymongo.errors.ServerSelectionTimeoutError:
        pytest.exit("DB is probably not running")

    yield client
    client.close()


@pytest.fixture
def empty_data(
    request: FixtureRequest,
    workdir: Path,
    shared_mongo_client: pymongo.MongoClient,
) -> FixtureData:
    """Yield an empty CTFApp object.

    :return: A CTFApp object, a path to the temporary directory,
    list of projects and users.
    :rtype: Iterator[FixtureData]
    """

    def teardown():
        ctf_app.user_cluster_mgr.remove_docs_by_filter()
        ctf_app.project_cluster_mgr.remove_docs_by_filter()
        ctf_app.enroll_mgr.remove_docs_by_filter()
        ctf_app.prj_mgr.remove_docs_by_filter()
        ctf_app.user_mgr.remove_docs_by_filter()

    # get data
    env_info = get_env_info()
    os.environ["LOG_DEST"] = str(workdir.resolve())

    YamlParser.init_parser()
    share_root = workdir / "share"
    if share_root.exists():
        shutil.rmtree(share_root)
    paths = PathDict(
        **{
            "projects": workdir / "share" / "project",
            "users": workdir / "share" / "user",
            "modules": workdir / "share" / "module",
            "scenarios": workdir / "share" / "scenario",
        }
    )

    # init testing env and clear database (just in case)
    ctf_app = CTFApp(env_info, paths, shared_mongo_client)

    ctf_app.user_cluster_mgr.remove_docs_by_filter()
    ctf_app.project_cluster_mgr.remove_docs_by_filter()
    ctf_app.enroll_mgr.remove_docs_by_filter()
    ctf_app.user_mgr.remove_docs_by_filter()
    ctf_app.prj_mgr.remove_docs_by_filter()

    # make a shadow dir
    request.addfinalizer(teardown)
    return ctf_app, workdir


@pytest.fixture
def project_data(
    empty_data: FixtureData,
) -> FixtureData:
    """Yield a CTFApp with 2 projects and destination directory.

    The manager contains following objects:
        Projects [enrolled]:
            - prj1 - []
            - prj2 - []

    :return: A CTFApp object, a path to the temporary directory,
    list of projects and users.
    :rtype: Iterator[FixtureData]
    """

    # init testing env
    ctf_app, tmp_path = empty_data
    ctf_app.setup_env_from_file(fixture_path() / "project_data.yaml")
    assert len(ctf_app.prj_mgr.get_docs()) == 2

    # yield data
    return ctf_app, tmp_path


@pytest.fixture
def user_data(
    empty_data: FixtureData,
) -> FixtureData:
    """Yield a CTFApp with 3 users and destination directory.

    The manager contains following objects:
        Users [enrolled]:
            - user1 - []
            - user2 - []
            - user3 - []

    :return: A CTFApp object, a path to the temporary directory,
        list of projects and users.
    :rtype: Iterator[FixtureData]
    """
    # init testing env
    ctf_app, tmp_path = empty_data
    ctf_app.setup_env_from_file(fixture_path() / "user_data.yaml")
    assert len(ctf_app.user_mgr.get_docs()) == 3

    # yield data
    return ctf_app, tmp_path


@pytest.fixture
def unconnected_data(
    empty_data: FixtureData,
) -> FixtureData:
    """Yield a CTFApp with 2 projects, 3 users, and destination directory.

    The manager contains following objects:
        Projects [enrolled]:
            - prj1 - []
            - prj2 - []
        Users [enrolled]:
            - user1 - []
            - user2 - []
            - user3 - []

    :return: A CTFApp object, a path to the temporary directory,
    list of projects and users.
    :rtype: Iterator[FixtureData]
    """
    # init testing env
    ctf_app, tmp_path = empty_data
    ctf_app.setup_env_from_file(fixture_path() / "unconnected_data.yaml")
    assert len(ctf_app.prj_mgr.get_docs()) == 2 and len(ctf_app.user_mgr.get_docs()) == 3

    # yield data
    return ctf_app, tmp_path


@pytest.fixture
def connected_data(
    empty_data: FixtureData,
) -> FixtureData:
    """Yield a CTFApp with 2 projects, 3 users, and destination directory.

    The manager contains following objects:
        Projects [enrolled]:
            - prj1 - [user2, user3]
            - prj2 - [user1, user2]
        Users [enrolled]:
            - user1 - [prj2]
            - user2 - [prj1, prj2]
            - user3 - [prj1]

    :return: A CTFApp object, a path to the temporary directory,
    list of projects and users.
    :rtype: Iterator[FixtureData]
    """
    # init testing env
    ctf_app, tmp_path = empty_data
    ctf_app.setup_env_from_file(fixture_path() / "connected_data.yaml")

    assert len(ctf_app.enroll_mgr.get_enrolled_projects("user2")) == 2

    # yield data
    return ctf_app, tmp_path


@pytest.fixture
def cli_data(connected_data: FixtureData) -> CLIData:
    ctf_app, tmp_path = connected_data
    os.environ.update(_base_path_dict(tmp_path))
    return ctf_app, tmp_path, CliRunner()


@pytest.fixture
def empty_cli_data(empty_data: FixtureData) -> CLIData:
    ctf_app, tmp_path = empty_data
    os.environ.update(_base_path_dict(tmp_path))
    return ctf_app, tmp_path, CliRunner()


@pytest.fixture
def tui_app(connected_data: FixtureData) -> App:
    ctf_app, tmp_path = connected_data
    user_share = (tmp_path / "share" / "user").resolve()
    user_share.mkdir(parents=True, exist_ok=True)
    os.environ["USER_SHARE_DIR"] = str(user_share)
    locale_file = user_share / "rendezvous_locale"
    if locale_file.is_file():
        locale_file.unlink()
    rendezvous_i18n.reset_locale_cache()
    os.environ.pop("FIT_RENDEZVOUS_LANG", None)
    return RendezvousApp(ctf_app)


@pytest.fixture
def empty_complex(empty_data: FixtureData) -> ComplexData:
    ctf_app, path = empty_data
    os.environ.update(_base_path_dict(path))
    return (CliRunner(), RendezvousApp(ctf_app), path)
