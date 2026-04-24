import pytest
from dateutil import parser

from fit_ctf.models.infra.secret_slots import composite_secret_id
from fit_ctf.models.utils.exceptions import (
    SecretAlreadySubmittedException,
    SecretNotFoundException,
)
from tests import FixtureData


def test_empty_progress(connected_data: FixtureData):
    ctf_app, _ = connected_data
    enrollment = ctf_app.enroll_mgr.get_enrollment(
        ctf_app.user_mgr.get_user("user2"), ctf_app.prj_mgr.get_project("prj2")
    )
    progress = enrollment.progress
    assert not progress.solved_secrets
    assert progress.found_secrets == 0
    assert not progress.last_submit_time

    enrollment = ctf_app.enroll_mgr.get_enrollment(
        ctf_app.user_mgr.get_user("user1"), ctf_app.prj_mgr.get_project("prj2")
    )
    progress = enrollment.progress
    assert len(progress.solved_secrets) == 1
    assert progress.found_secrets == 1
    assert progress.last_submit_time and progress.last_submit_time == parser.parse(
        "2025-09-27T18:09:25.594Z"
    )


def test_submit_secret(connected_data: FixtureData):
    ctf_app, _ = connected_data
    user1 = ctf_app.user_mgr.get_user("user1")
    enrollment = ctf_app.enroll_mgr.get_enrollment(
        user1, ctf_app.prj_mgr.get_project("prj2")
    )

    timestamp = parser.parse("2025-10-01T00:00:00.000Z")
    assert (
        enrollment.progress.last_submit_time
        and enrollment.progress.last_submit_time < timestamp
        and enrollment.progress.found_secrets == 1
    )

    cid_key2 = composite_secret_id("user", "login_node", "key2")
    assert cid_key2 not in enrollment.progress.solved_secrets
    log_len_before = len(enrollment.progress.submission_log)
    with pytest.raises(SecretNotFoundException):
        ctf_app.enroll_mgr.submit_secret(enrollment, "wrong secret")

    assert len(enrollment.progress.submission_log) == log_len_before + 1

    ctf_app.enroll_mgr.submit_secret(enrollment, "value2")
    rec = enrollment.progress.solved_secrets[cid_key2]
    assert rec.submitted_at and rec.user_id == user1.id
    with pytest.raises(SecretAlreadySubmittedException):
        ctf_app.enroll_mgr.submit_secret(enrollment, "value2")

    assert enrollment.progress.found_secrets == 2
    assert enrollment.progress.last_submit_time > timestamp


def test_list_secrets_for_display(connected_data: FixtureData):
    ctf_app, _ = connected_data
    enrollment = ctf_app.enroll_mgr.get_enrollment(
        ctf_app.user_mgr.get_user("user1"), ctf_app.prj_mgr.get_project("prj2")
    )
    rows = ctf_app.enroll_mgr.list_secrets_for_display(enrollment)
    assert len(rows) == 2
    names = {r["name"] for r in rows}
    assert "user/login_node/key1" in names
    assert "user/login_node/key2" in names


def test_leaderboard(connected_data: FixtureData):
    ctf_app, _ = connected_data
    prj = ctf_app.prj_mgr.get_project("prj2")
    leaderboard_data = ctf_app.enroll_mgr.get_leaderboard(prj)
    assert len(leaderboard_data) == len(
        ctf_app.enroll_mgr.get_enrollments_for_project("prj2")
    )
    assert leaderboard_data[0]["user"] == "user1"

    user = ctf_app.user_mgr.get_user("user2")
    enrollment = ctf_app.enroll_mgr.get_enrollment(user, prj)
    uc = ctf_app.user_cluster_mgr.get_cluster(enrollment)
    cfg = uc.scenario_configs["login_node"]
    cfg.secrets["dyn1"] = "secret-value1"
    cfg.secrets["dyn2"] = "secret-value2"
    ctf_app.user_cluster_mgr.create_or_update_scenario_config(uc, cfg)

    enrollment = ctf_app.enroll_mgr.get_enrollment(user, prj)
    assert ctf_app.enroll_mgr.count_submittable_slots(enrollment) == 2
    assert ctf_app.enroll_mgr.get_leaderboard(prj)[0]["user"] == "user1"

    ctf_app.enroll_mgr.submit_secret(enrollment, "secret-value1")
    assert ctf_app.enroll_mgr.get_leaderboard(prj)[0]["user"] == "user1"

    ctf_app.enroll_mgr.submit_secret(enrollment, "secret-value2")
    assert ctf_app.enroll_mgr.get_leaderboard(prj)[0]["user"] == "user2"
