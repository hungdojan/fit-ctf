from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import fit_ctf.ctf_base as _ctf_base


class LoggerInterface(ABC):
    def __init__(self, ctf_base: "_ctf_base.CTFBase", **kwargs):
        self._ctf_base = ctf_base

    @property
    def ctf_base(self) -> "_ctf_base.CTFBase":
        return self._ctf_base

    @abstractmethod
    def info(self, msg: str, **kwargs):
        pass

    @abstractmethod
    def error(self, msg: str, **kwargs):
        pass

    @abstractmethod
    def warning(self, msg: str, **kwargs):
        pass

    @abstractmethod
    def critical(self, msg: str, **kwargs):
        pass

    @abstractmethod
    def debug(self, msg: str, **kwargs):
        pass

    @abstractmethod
    def print(self, msg: str, **kwargs):
        pass
