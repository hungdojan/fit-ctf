from abc import ABC, abstractmethod

import fit_ctf.ctf_base as ctf_base
import fit_ctf_models.project as _prj
import fit_ctf_models.user as _user
from fit_ctf_components.base import BaseComponent


class SecretManagerInterface(ABC, BaseComponent):
    def __init__(self, ctf_base: "ctf_base.CTFBase"):
        BaseComponent.__init__(self, ctf_base)

    @abstractmethod
    def generate_hash(
        self, data: str, user: "_user.User", project: "_prj.Project", **kw
    ) -> str:
        pass
