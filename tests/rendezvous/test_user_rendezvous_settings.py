import os
from pathlib import Path

import pytest

from fit_ctf.path_mgmt import PathManagement
from fit_ctf_components.types import PathDict, UserRole
from fit_ctf_models.user import User
from fit_ctf_rendezvous.user_rendezvous_settings import (
    SETTINGS_FILENAME,
    RendezvousUserSettings,
    default_settings,
    load,
    save,
)

if os.getenv("ENABLE_RENDEZVOUS_TESTING", "0") == "0":
    pytest.skip("Rendezvous TUI app testing not enabled", allow_module_level=True)


def _paths(tmp_path: Path) -> PathManagement:
    return PathManagement(
        PathDict(
            projects=tmp_path / "p",
            users=tmp_path / "u",
            modules=tmp_path / "m",
            scenarios=tmp_path / "s",
        )
    )


def _user(name: str) -> User:
    return User(username=name, password="x", role=UserRole.USER)


def test_load_missing_returns_defaults(tmp_path: Path):
    paths = _paths(tmp_path)
    assert load(paths, _user("alice")) == default_settings()


def test_save_load_roundtrip(tmp_path: Path):
    paths = _paths(tmp_path)
    u = _user("bob")
    save(
        paths,
        u,
        RendezvousUserSettings.create(locale="cs", dark_theme=True),
    )
    fp = paths.user_path(u) / SETTINGS_FILENAME
    assert fp.is_file()
    got = load(paths, u)
    assert got.locale == "cs"
    assert got.dark_theme is True


def test_load_invalid_json_ignored(tmp_path: Path):
    paths = _paths(tmp_path)
    u = _user("carol")
    d = paths.user_path(u)
    d.mkdir(parents=True)
    (d / SETTINGS_FILENAME).write_text("{not json", encoding="utf-8")
    assert load(paths, u) == default_settings()
