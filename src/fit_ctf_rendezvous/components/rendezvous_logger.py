from abc import ABCMeta

from textual.message_pump import _MessagePumpMeta
from textual.widgets import Log

from fit_ctf.ctf_base import CTFBase
from fit_ctf_components.logger.logger_interface import LoggerInterface


class CombinedMeta(_MessagePumpMeta, ABCMeta):
    pass


class RendezvousLogger(Log, LoggerInterface, metaclass=CombinedMeta):

    def __init__(
        self,
        ctf_base: CTFBase,
        **kwargs,
    ) -> None:
        Log.__init__(self, **kwargs)
        LoggerInterface.__init__(self, ctf_base)
        ctf_base.register_component("logger", self)

    def info(self, msg: str, **kwargs):
        self.print(msg)

    def error(self, msg: str, **kwargs):
        self.print(msg)

    def warning(self, msg: str, **kwargs):
        self.print(msg)

    def debug(self, msg: str, **kwargs):
        self.print(msg)

    def critical(self, msg: str, **kwargs):
        self.print(msg)

    def print(self, msg: str, **kwargs):
        if self.is_mounted:
            self.write_line(msg)
