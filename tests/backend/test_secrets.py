import os
from fit_ctf_models.secret import SecretManager
from tests import FixtureData


def test_secret_mgr(empty_data: FixtureData):
    assert SecretManager._app_secret == os.getenv("APP_SECRET", "").encode()


def test_compute_search_index(empty_data: FixtureData):
    plain_text = "test_secret"
    index = SecretManager.compute_search_index(plain_text)
    assert index == SecretManager.compute_search_index(plain_text)
    assert index != plain_text
    assert index != SecretManager.compute_search_index("different_secret")


def test_encrypt_and_decrypt(empty_data: FixtureData):
    plain_text = "test_secret"
    n1, ct1 = SecretManager.encrypt(plain_text)
    assert ct1 != plain_text
    assert SecretManager.decrypt(n1, ct1) == plain_text

    n2, ct2 = SecretManager.encrypt(plain_text)
    while n1 == n2:
        n2, ct2 = SecretManager.encrypt(plain_text)

    assert ct2 != ct1
    assert SecretManager.decrypt(n2, ct2) == plain_text
