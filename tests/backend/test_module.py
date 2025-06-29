from pathlib import Path

import pytest

from fit_ctf_templates import TEMPLATE_DIRNAME
from fit_ctf_components.exceptions import (
    ModuleExistsException,
    ModuleInUseException,
    ModuleNotExistsException,
)
from tests import FixtureData


def test_base_modules(empty_data: FixtureData):
    # init testing env
    ctf_app, _ = empty_data
    assert ctf_app._paths["modules"].is_dir()
    module_names = [path.name for path in ctf_app._paths["modules"].iterdir()]
    assert set(module_names) == {"base", "base_ssh"}


def test_list_modules(empty_data: FixtureData):
    ctf_app, _ = empty_data
    for name, path in ctf_app.module_mgr.list_modules().items():
        assert name in {"base", "base_ssh"}
        assert path.is_dir()


async def test_create_module(
    empty_data: FixtureData,
):
    # init testing env
    ctf_app, _ = empty_data
    module_mgr = ctf_app.module_mgr
    with pytest.raises(ModuleExistsException):
        module_mgr.create_module("base")
    module_mgr.create_module("new_module")
    module_path = module_mgr.get_path("new_module")
    assert module_path.is_dir()
    assert set([path.name for path in module_path.iterdir()]) == set(
        [path.name for path in (Path(TEMPLATE_DIRNAME) / "v1" / "modules").iterdir()]
    )

    # teardown
    await module_mgr.remove_module("new_module")


async def test_reference_count(connected_data: FixtureData):
    ctf_app, _ = connected_data
    prj = ctf_app.prj_mgr.get_docs()[0]
    assert ctf_app.module_mgr.reference_count(prj.name) == {"base": 1, "base_ssh": 2}
    assert ctf_app.module_mgr.reference_count(None) == {"base": 2, "base_ssh": 4}

    await ctf_app.ue_mgr.cancel_user_enrollment(
        ctf_app.ue_mgr.get_user_enrollments_for_project(prj)[0], prj
    )

    assert ctf_app.module_mgr.reference_count(prj.name) == {"base": 1, "base_ssh": 1}


async def test_remove_module(connected_data: FixtureData):
    ctf_app, _ = connected_data
    for prj in ctf_app.prj_mgr.get_docs():
        await ctf_app.ue_mgr.cancel_all_project_enrollments(prj)
    module_path = ctf_app.module_mgr.list_modules()["base_ssh"]
    assert module_path.is_dir()
    await ctf_app.module_mgr.remove_module("base_ssh")
    assert not module_path.is_dir()


async def test_error_states(connected_data: FixtureData):
    ctf_app, _ = connected_data
    module_mgr = ctf_app.module_mgr
    with pytest.raises(ModuleExistsException):
        module_mgr.create_module("base")
    with pytest.raises(ModuleNotExistsException):
        module_mgr.get_path("random_module")
    with pytest.raises(ModuleInUseException):
        await module_mgr.remove_module("base_ssh")
