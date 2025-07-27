from tests import FixtureData


def test_manager(empty_data: FixtureData):
    ctf_app, _ = empty_data
    assert ctf_app.up_mgr is not None


def test_generate_secret_hash(empty_data: FixtureData):
    pass
