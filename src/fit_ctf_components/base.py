from typing import TypeVar

import fit_ctf.ctf_base

ComponentType = TypeVar("ComponentType", bound="BaseComponent")


class BaseComponent:
    def __init__(self, ctf_base: "fit_ctf.ctf_base.CTFBase") -> None:
        self._ctf_base = ctf_base

    @property
    def ctf_base(self) -> "fit_ctf.ctf_base.CTFBase":
        return self._ctf_base
