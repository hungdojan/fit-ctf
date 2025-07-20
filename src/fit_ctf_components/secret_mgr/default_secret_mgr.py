import os
from hashlib import blake2b

import fit_ctf.ctf_base as ctf_base
import fit_ctf_models.project as _prj
import fit_ctf_models.user as _user
from fit_ctf_components.secret_mgr.secret_mgr_interface import SecretManagerInterface


class DefaultSecretManager(SecretManagerInterface):
    def __init__(self, ctf_base: "ctf_base.CTFBase"):
        super().__init__(ctf_base)

    def generate_hash(
        self, data: str, user: "_user.User", project: "_prj.Project", **kw
    ) -> str:
        h = blake2b(
            key=data.encode(),
            salt=f"{project.name}-{os.getenv('APP_SECRET')}".encode(),
            person=user.username.encode(),
        )
        return h.digest().decode()
