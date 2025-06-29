from tests import FixtureData


def test_empty(empty_data: FixtureData):
    ctf_app, _ = empty_data
    assert ctf_app
    assert len(ctf_app.prj_mgr.get_docs()) == 0
    assert len(ctf_app.user_mgr.get_docs()) == 0
    assert len(ctf_app.ue_mgr.get_docs()) == 0


def test_file_structure(empty_data: FixtureData):
    _, paths = empty_data
    share_path = paths / "share"
    assert (share_path / "project").exists() and (share_path / "project").is_dir()
    assert (share_path / "user").exists() and (share_path / "user").is_dir()
    assert (share_path / "module").exists() and (share_path / "module").is_dir()
