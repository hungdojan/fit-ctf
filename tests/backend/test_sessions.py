from datetime import datetime, timezone

from freezegun import freeze_time

from tests import FixtureData


def test_user_login(connected_data: FixtureData):
    ctf_app, _ = connected_data
    user = ctf_app.user_mgr.get_user("user1")
    assert user
    assert not user.sessions

    time_freeze = datetime(2026, 2, 15, 20, 0, tzinfo=timezone.utc)
    with freeze_time(time_freeze):
        ctf_app.user_mgr.record_login(user)
    assert user.sessions[-1].timestamp.replace(tzinfo=timezone.utc) == time_freeze

    time_freeze = datetime(2026, 2, 16, 2, 0, tzinfo=timezone.utc)
    with freeze_time(time_freeze):
        ctf_app.user_mgr.record_logout(user)
    assert user.sessions[-1].timestamp.replace(tzinfo=timezone.utc) == time_freeze
