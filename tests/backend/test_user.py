import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from fit_ctf_components.auth.local_auth import LocalAuth
from fit_ctf_models.utils.exceptions import (
    PublicKeyUploadFail,
    UserExistsException,
    UserNotExistsException,
)
from tests import FixtureData


# empty data
def test_empty_mgr(empty_data: FixtureData):
    ctf_app, _ = empty_data
    user_mgr = ctf_app.user_mgr
    assert len(user_mgr.get_users_info(True)) == 0


def test_create_user(empty_data: FixtureData):
    ctf_app, _ = empty_data
    user_mgr = ctf_app.user_mgr

    assert len(user_mgr.get_users_info(True)) == 0
    assert not [i for i in ctf_app._paths["users"].iterdir()]

    user_data: dict = {"username": "user1", "password": "StrongPassword12"}
    user_doc, credentials = user_mgr.create_new_user(**user_data)

    assert len(user_mgr.get_users_info(True)) == 1
    assert credentials["password"] == user_data["password"]
    assert user_mgr.get_user(user_doc.username)
    assert len(list(ctf_app._paths["users"].iterdir())) == 1
    assert (ctf_app._paths["users"] / user_data["username"]).is_dir()


def test_create_multiple_users(user_data: FixtureData):
    ctf_app, _ = user_data
    user_mgr = ctf_app.user_mgr
    assert len(user_mgr.get_docs()) == 3

    users = user_mgr.create_multiple_users([f"user{i+1}" for i in range(5)])
    assert len(user_mgr.get_docs()) == 5
    assert {"user4", "user5"} == set([u["username"] for u in users])
    assert (ctf_app._paths["users"] / "user4").is_dir() and (
        ctf_app._paths["users"] / "user5"
    ).is_dir()


def test_get_users(connected_data: FixtureData):
    ctf_app, _ = connected_data
    users = ctf_app.user_mgr.get_users_info()
    assert len(users) == 3
    assert set(users[0].keys()) == {"username", "active", "projects", "email", "role"}


def test_get_user_raw(user_data: FixtureData):
    ctf_app, _ = user_data
    with pytest.raises(UserNotExistsException):
        user = ctf_app.user_mgr.get_user_raw("user10")

    user = ctf_app.user_mgr.get_user_raw("user1")
    assert {"username", "active", "email", "role"} == set(list(user.keys()))
    assert user["username"] == "user1"
    assert user["active"]


async def test_disable_user(connected_data: FixtureData):
    ctf_app, _ = connected_data

    assert len(ctf_app.user_mgr.get_docs()) == 3
    assert len(ctf_app.ue_mgr.get_user_enrollments_for_project("prj2")) == 2

    await ctf_app.user_mgr.disable_user("user1")
    assert len(ctf_app.user_mgr.get_docs()) == 3
    assert len(ctf_app.user_mgr.get_users_info(True)) == 2
    assert len(ctf_app.ue_mgr.get_user_enrollments_for_project("prj2")) == 1


async def test_flush_user(connected_data: FixtureData):
    ctf_app, _ = connected_data

    assert len(ctf_app.user_mgr.get_docs()) == 3
    with pytest.raises(UserExistsException):
        ctf_app.user_mgr.flush_user("user1")

    await ctf_app.user_mgr.disable_user("user1")
    assert len(ctf_app.user_mgr.get_docs()) == 3
    assert (ctf_app._paths["users"] / "user1").is_dir()

    ctf_app.user_mgr.flush_user("user1")
    assert len(ctf_app.user_mgr.get_docs()) == 2
    assert not (ctf_app._paths["users"] / "user1").is_dir()


async def test_delete_user(connected_data: FixtureData):
    ctf_app, _ = connected_data

    assert len(ctf_app.user_mgr.get_docs()) == 3
    assert (ctf_app._paths["users"] / "user1").is_dir()

    await ctf_app.user_mgr.delete_a_user("user1")

    assert len(ctf_app.user_mgr.get_docs()) == 2
    assert not (ctf_app._paths["users"] / "user1").is_dir()


async def test_delete_multiple_users(connected_data: FixtureData):
    ctf_app, _ = connected_data

    assert len(ctf_app.user_mgr.get_docs()) == 3
    assert len(list(ctf_app._paths["users"].iterdir())) == 3

    await ctf_app.user_mgr.delete_users(["user1", "user2", "user4"])

    assert len(ctf_app.user_mgr.get_docs()) == 1
    assert len(list(ctf_app._paths["users"].iterdir())) == 1


def test_change_password(user_data: FixtureData):
    ctf_app, _ = user_data
    local_auth = LocalAuth(ctf_app.user_mgr)

    assert local_auth.validate_credentials("user1", "user1Password")
    ctf_app.user_mgr.change_password("user1", "newStrongPassw0rd")
    assert not local_auth.validate_credentials("user1", "user1Password")
    assert local_auth.validate_credentials("user1", "newStrongPassw0rd")


def test_user_errors(connected_data: FixtureData):
    ctf_app, _ = connected_data
    with pytest.raises(UserNotExistsException):
        ctf_app.user_mgr.get_user("unknownUser")
    with pytest.raises(UserExistsException):
        ctf_app.user_mgr.create_new_user("user1", "StrongPassword12")
    with pytest.raises(UserNotExistsException):
        ctf_app.user_mgr.flush_user("user10")


def test_upload_public_key(user_data: FixtureData):
    ctf_app, _ = user_data
    user = ctf_app.user_mgr.get_user("user1")
    with pytest.raises(PublicKeyUploadFail):
        ctf_app.user_mgr.upload_public_key(user, b"random_bytes")

    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    )

    ssh_dir = ctf_app.user_mgr.paths.user_path(user) / "home" / ".ssh"
    assert not ssh_dir.exists()
    ctf_app.user_mgr.upload_public_key(user, public_key_bytes)
    assert ssh_dir.exists()
    authorized_keys_file = ssh_dir / "authorized_keys"
    assert (
        authorized_keys_file.exists()
        and len(authorized_keys_file.read_bytes().splitlines()) == 1
    )

    ctf_app.user_mgr.upload_public_key(user, public_key_bytes)
    assert (
        authorized_keys_file.exists()
        and len(authorized_keys_file.read_bytes().splitlines()) == 1
        and authorized_keys_file.read_bytes().strip() == public_key_bytes
    )


# # user data
#
# def test_validate_user_login(
#     user_data: FixtureData,
# ):
#     ctf_app, _ = user_data
#     user_mgr = ctf_app.user_mgr
#     assert not user_mgr.validate_user_login("nope", "what")
#
#     assert not user_mgr.validate_user_login("user1", "user1")
#     assert user_mgr.validate_user_login("user1", "user1Password")
#
#
# def test_get_password_hash(
#     user_data: FixtureData,
# ):
#     ctf_app, _ = user_data
#     user_mgr = ctf_app.user_mgr
#
#     assert not usrs[0].password == user_mgr.get_password_hash("wrong_password")
#     assert usrs[0].password == user_mgr.get_password_hash(f"{usrs[0].username}Password")
#
#
#
# # connected_data
# def test_get_active_projects_for_user(
#     connected_data: FixtureData,
# ):
#     ctf_app, _ = connected_data
#     user_mgr = ctf_app.user_mgr
#     expected_data = {"user1": {"prj2"}, "user2": {"prj1", "prj2"}, "user3": {"prj1"}}
#     for u in usrs:
#         data = expected_data[u.username]
#         prj_data = set(
#             [p.name for p in user_mgr.get_active_projects_for_user(u.username)]
#         )
#         assert data == prj_data
#
#
# def test_delete_a_user(
#     connected_data: FixtureData,
# ):
#     ctf_app, _ = connected_data
#     user_mgr = ctf_app.user_mgr
#     expected_data = {"user1": {}, "user2": {"prj1", "prj2"}, "user3": {"prj1"}}
#
#     user_mgr.delete_a_user("user1")
#     for u in user_mgr.get_docs():
#         assert (not u.active and len(expected_data[u.username]) == 0) or (
#             u.active and len(expected_data[u.username]) > 0
#         )
#
#     assert len(ctf_app.prj_mgr.get_active_users_for_project("prj1")) == 2
#     assert len(ctf_app.prj_mgr.get_active_users_for_project("prj2")) == 1
#
#
# def test_get_active_projects_for_user_raw(
#     connected_data: FixtureData,
# ):
#     ctf_app, _ = connected_data
#     user_mgr = ctf_app.user_mgr
#
#     prjs = user_mgr.get_active_projects_for_user_raw("user2")
#     for prj in prjs:
#         assert all(
#             k in prj for k in {"name", "active", "max_nof_users", "active_users"}
#         )
#         assert prj["active"]
#         assert prj["active_users"] == 2
#
#
# # static methods
#
#
# def test_validate_password_strength():
#     assert not UserManager.validate_password_strength("short")
#     assert not UserManager.validate_password_strength("very long password")
#     assert not UserManager.validate_password_strength("very long password with digit 1")
#     assert not UserManager.validate_password_strength(
#         "very long password with upper case U"
#     )
#     assert not UserManager.validate_password_strength("Sh0rt")
#
#     assert UserManager.validate_password_strength("ValidPassw0rd")
#
#
# def test_generate_password():
#     with pytest.raises(ValueError):
#         UserManager.generate_password(-1)
#
#     assert UserManager.generate_password(0) == ""
#     assert len(UserManager.generate_password(10)) == 10
#     assert len(UserManager.generate_password(8)) == 8
#
#
# def test_validate_username_format():
#     assert not UserManager.validate_username_format("gg")
#     assert not UserManager.validate_username_format("invalid-name")
#     assert not UserManager.validate_username_format("space space")
#     assert not UserManager.validate_username_format("spec. characters!")
#     assert not UserManager.validate_username_format("under_score")
#
#     assert UserManager.validate_username_format("ssss")
#     assert UserManager.validate_username_format("numbers1")
