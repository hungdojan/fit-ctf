import base64
import hashlib
import hmac
import os
from datetime import datetime
from typing import Any

from bson import ObjectId
from bson.binary import Binary
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pydantic import BaseModel, ConfigDict


class Secret(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True)
    search_index: str
    nonce: Binary
    enc_secret: Binary
    submitted: datetime | None = None
    user_id: ObjectId | None = None

    def model_dump(self, by_alias: bool = True, **kw) -> dict[str, Any]:
        return super().model_dump(by_alias=by_alias, **kw)


class SecretManager:
    _app_secret: bytes
    ENC_KEY: bytes
    IDX_KEY: bytes
    IDX_SALT: bytes

    @classmethod
    def init_class(cls, app_secret: str) -> None:
        cls._app_secret = app_secret.encode()
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=80,
            salt=b"FIT_CTF:v1:enc+search",
            info=b"enc+search",
            backend=default_backend(),
        )
        okm = hkdf.derive(cls._app_secret)
        cls.ENC_KEY = okm[:32]
        cls.IDX_KEY = okm[32:64]
        cls.IDX_SALT = okm[64:80]

    @classmethod
    def compute_search_index(cls, secret: str) -> str:
        prehash = hashlib.scrypt(
            password=secret.encode(), salt=cls.IDX_SALT, n=2**15, r=8, p=1, dklen=32
        )
        mac = hmac.new(cls.IDX_KEY, prehash, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(mac).decode().rstrip("=")

    @classmethod
    def encrypt(cls, secret: str) -> tuple[bytes, bytes]:
        """Encrypt a secret.

        Generates a nonce and a cipher text.
        :param secret: A secret value.
        :type secret: str
        :return: A pair of nonce and cipher_text
        :rtype: tuple[bytes, bytes]
        """
        aes = AESGCM(cls.ENC_KEY)
        nonce = os.urandom(12)
        cipher_text = aes.encrypt(nonce, secret.encode(), associated_data=None)
        return nonce, cipher_text

    @classmethod
    def decrypt(cls, nonce: bytes, cipher_text: bytes) -> str:
        """Decrypt the secret

        Decrypts the secret from the nonce and cipher text.
        :param nonce: A nonce generated during the encryption.
        :type nonce: bytes
        :param cipher_text: A cipher text to decrypt.
        :type cipher_text: bytes
        :return: A decrypted secret.
        :rtype: str
        """
        aes = AESGCM(cls.ENC_KEY)
        plain_text = aes.encrypt(nonce, cipher_text, associated_data=None)
        return plain_text.decode()
