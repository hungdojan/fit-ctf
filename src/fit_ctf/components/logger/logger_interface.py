from abc import ABC, abstractmethod

import fit_ctf.ctf_base as ctf_base
from fit_ctf.components.base import BaseComponent


class LoggerInterface(ABC, BaseComponent):
    def __init__(self, ctf_base: "ctf_base.CTFBase", **kwargs):
        BaseComponent.__init__(self, ctf_base, **kwargs)

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
