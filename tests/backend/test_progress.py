import pytest
from dateutil import parser

from fit_ctf_models.utils.exceptions import (
    SecretAlreadySubmittedException,
    SecretNameAlreadyExistsException,
    SecretNotFoundException,
    SecretValueCollision,
)
from tests import FixtureData


def test_empty_progress(connected_data: FixtureData):
    ctf_app, _ = connected_data
    ue = ctf_app.ue_mgr.get_user_enrollment(
        ctf_app.user_mgr.get_user("user2"), ctf_app.prj_mgr.get_project("prj2")
    )
    progress = ue.progress
    assert not progress.secrets
    assert progress.found_secrets == 0
    assert not progress.last_submit_time

    ue = ctf_app.ue_mgr.get_user_enrollment(
        ctf_app.user_mgr.get_user("user1"), ctf_app.prj_mgr.get_project("prj2")
    )
    progress = ue.progress
    assert len(progress.secrets) == 2
    assert progress.found_secrets == 1
    assert progress.last_submit_time and progress.last_submit_time == parser.parse(
        "2025-09-27T18:09:25.594Z"
    )


def test_add_secret(connected_data: FixtureData):
    ctf_app, _ = connected_data
    ue = ctf_app.ue_mgr.get_user_enrollment(
        ctf_app.user_mgr.get_user("user2"), ctf_app.prj_mgr.get_project("prj2")
    )
    progress = ue.progress
    assert not progress.secrets
    assert progress.found_secrets == 0
    assert not progress.last_submit_time
    assert not progress.list_secrets()

    ctf_app.ue_mgr.add_secret(ue, "new_secret", "test-secret")
    assert progress.secrets
    assert progress.found_secrets == 0
    assert not progress.last_submit_time
    assert progress.list_secrets()
    secret = progress.get_secret_by_name("new_secret")
    assert (
        secret
        and secret.submitted is None
        and secret.user_id is None
        and "test-secret" not in secret.nonce
        and "test-secret" not in secret.search_index
        and "test-secret" not in secret.enc_secret
    )

    with pytest.raises(SecretNameAlreadyExistsException):
        ctf_app.ue_mgr.add_secret(ue, "new_secret", "test-secret")
    with pytest.raises(SecretValueCollision):
        ctf_app.ue_mgr.add_secret(ue, "another_secret", "test-secret")


def test_update_secret(connected_data: FixtureData):
    ctf_app, _ = connected_data
    ue = ctf_app.ue_mgr.get_user_enrollment(
        ctf_app.user_mgr.get_user("user1"), ctf_app.prj_mgr.get_project("prj2")
    )
    progress = ue.progress

    with pytest.raises(SecretNotFoundException):
        ctf_app.ue_mgr.update_secret_value(ue, "new-secret-name", "new-value")
    with pytest.raises(SecretValueCollision):
        ctf_app.ue_mgr.update_secret_value(ue, "key2", "value1")

    assert progress.get_secret_by_value("value2")
    ctf_app.ue_mgr.update_secret_value(ue, "key2", "new-value")
    assert not progress.get_secret_by_value("value2")
    assert progress.get_secret_by_value("new-value")

    assert progress.found_secrets == 1
    with pytest.raises(SecretValueCollision):
        ctf_app.ue_mgr.update_secret_value(ue, "key2", "new-value")

    assert progress.found_secrets > 0 and progress.last_submit_time
    ctf_app.ue_mgr.update_secret_value(ue, "key1", "first_change")
    assert progress.found_secrets > 0 and progress.last_submit_time
    ctf_app.ue_mgr.update_secret_value(ue, "key1", "second_change", True)
    assert progress.found_secrets == 0 and not progress.last_submit_time


def test_delete_secret(connected_data: FixtureData):
    ctf_app, _ = connected_data
    ue = ctf_app.ue_mgr.get_user_enrollment(
        ctf_app.user_mgr.get_user("user1"), ctf_app.prj_mgr.get_project("prj2")
    )
    assert len(ue.progress.list_secrets()) == 2
    ctf_app.ue_mgr.delete_secret(ue, "new-secret-name")
    assert len(ue.progress.list_secrets()) == 2
    with pytest.raises(SecretNotFoundException):
        ctf_app.ue_mgr.delete_secret(ue, "new-secret-name", False)

    ctf_app.ue_mgr.delete_secret(ue, "key1")
    assert len(ue.progress.list_secrets()) == 1
    with pytest.raises(SecretNotFoundException):
        ctf_app.ue_mgr.delete_secret(ue, "key1", False)
    ctf_app.ue_mgr.delete_secret(ue, "key2")
    assert not ue.progress.list_secrets()


def test_submit_secret(connected_data: FixtureData):
    ctf_app, _ = connected_data
    user1 = ctf_app.user_mgr.get_user("user1")
    ue = ctf_app.ue_mgr.get_user_enrollment(user1, ctf_app.prj_mgr.get_project("prj2"))

    # a date after the last submission
    timestamp = parser.parse("2025-10-01T00:00:00.000Z")
    assert (
        ue.progress.last_submit_time
        and ue.progress.last_submit_time < timestamp
        and ue.progress.found_secrets == 1
    )

    new_secret = ue.progress.get_secret_by_name("key2")
    assert new_secret and not new_secret.submitted and not new_secret.user_id
    with pytest.raises(SecretNotFoundException):
        ctf_app.ue_mgr.submit_secret(ue, "wrong secret")
    ctf_app.ue_mgr.submit_secret(ue, "value2")
    assert new_secret.submitted and new_secret.user_id == user1.id
    with pytest.raises(SecretAlreadySubmittedException):
        ctf_app.ue_mgr.submit_secret(ue, "value2")

    assert ue.progress.found_secrets == 2 and ue.progress.last_submit_time > timestamp

    submitted_secret = ue.progress.get_secret_by_value("value2")
    assert (
        submitted_secret and submitted_secret.submitted == ue.progress.last_submit_time
    )


def test_progress_methods(connected_data: FixtureData):
    ctf_app, _ = connected_data
    ue = ctf_app.ue_mgr.get_user_enrollment(
        ctf_app.user_mgr.get_user("user1"), ctf_app.prj_mgr.get_project("prj2")
    )
    progress = ue.progress
    secret = progress.get_secret_by_name("key1")
    assert len(progress.list_secrets()) == 2
    assert secret and progress.get_last_submit() == secret.submitted
    assert progress.get_secret_by_name("key1") == progress.get_secret_by_value("value1")


def test_leaderboard(connected_data: FixtureData):
    ctf_app, _ = connected_data
    prj = ctf_app.prj_mgr.get_project("prj2")
    leaderboard_data = ctf_app.ue_mgr.get_leaderboard(prj)
    assert len(leaderboard_data) == len(
        ctf_app.ue_mgr.get_user_enrollments_for_project("prj2")
    )
    assert leaderboard_data[0]["user"] == "user1"

    user = ctf_app.user_mgr.get_user("user2")
    ue = ctf_app.ue_mgr.get_user_enrollment(user, prj)
    ctf_app.ue_mgr.add_secret(ue, "secret1", "secret-value1")
    ctf_app.ue_mgr.add_secret(ue, "secret2", "secret-value2")

    # reload from database
    ue = ctf_app.ue_mgr.get_user_enrollment(user, prj)
    assert ue and len(ue.progress.secrets.keys()) == 2
    assert ctf_app.ue_mgr.get_leaderboard(prj)[0]["user"] == "user1"

    # same number of secrets different time
    ctf_app.ue_mgr.submit_secret(ue, "secret-value1")
    assert ctf_app.ue_mgr.get_leaderboard(prj)[0]["user"] == "user1"

    # user2 has submitted more secrets
    ctf_app.ue_mgr.submit_secret(ue, "secret-value2")
    assert ctf_app.ue_mgr.get_leaderboard(prj)[0]["user"] == "user2"
