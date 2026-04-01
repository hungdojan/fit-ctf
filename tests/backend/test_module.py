import pytest

from fit_ctf_models.utils.exceptions import (
    ModuleExistsException,
    ModuleInUseException,
    ModuleNotExistsException,
)
from fit_ctf_templates import TEMPLATE_PATH_MAP
from tests import FixtureData


def test_list_modules(empty_data: FixtureData):
    ctf_app, _ = empty_data
    for name, path in ctf_app.module_mgr.list_modules().items():
        assert name in set(p.name for p in TEMPLATE_PATH_MAP["modules"].iterdir())
        assert path.is_dir()


async def test_create_module(
    empty_data: FixtureData,
):
    # init testing env
    ctf_app, _ = empty_data
    module_mgr = ctf_app.module_mgr
    with pytest.raises(ModuleExistsException):
        module_mgr.create_module("template")
    module_mgr.create_module("new_module")
    module_path = module_mgr.get_path("new_module")
    assert module_path.is_dir()
    assert set([path.name for path in module_path.iterdir()]) == set(
        [path.name for path in (TEMPLATE_PATH_MAP["modules"]).iterdir()]
    )

    # teardown
    await module_mgr.remove_module("new_module")


async def test_reference_count(connected_data: FixtureData):
    ctf_app, _ = connected_data

    prj = ctf_app.prj_mgr.get_docs()[0]
    assert ctf_app.module_mgr.reference_count(prj.name) == {"ssh_ubi": 2, "template": 1}
    assert ctf_app.module_mgr.reference_count(None) == {"ssh_ubi": 4, "template": 1}

    await ctf_app.enroll_mgr.cancel_enrollment(
        ctf_app.enroll_mgr.get_enrollments_for_project(prj)[0], prj
    )

    assert ctf_app.module_mgr.reference_count(prj.name) == {"template": 1, "ssh_ubi": 1}


async def test_remove_module(connected_data: FixtureData):
    ctf_app, _ = connected_data
    for prj in ctf_app.prj_mgr.get_docs():
        await ctf_app.enroll_mgr.cancel_all_project_enrollments(prj)
    module_path = ctf_app.module_mgr.list_modules()["ssh_debian"]
    assert module_path.is_dir()
    await ctf_app.module_mgr.remove_module("ssh_debian")
    assert not module_path.is_dir()


async def test_error_states(connected_data: FixtureData):
    ctf_app, _ = connected_data
    module_mgr = ctf_app.module_mgr
    with pytest.raises(ModuleExistsException):
        module_mgr.create_module("ssh_ubi")
    with pytest.raises(ModuleNotExistsException):
        module_mgr.get_path("random_module")
    with pytest.raises(ModuleInUseException):
        await module_mgr.remove_module("template")
