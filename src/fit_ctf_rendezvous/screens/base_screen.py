from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header

from fit_ctf_rendezvous.core_manager import CoreManager


class BaseScreen(Screen):

    def __init__(self, core_mgr: CoreManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self._core_mgr = core_mgr

    @property
    def core_mgr(self) -> CoreManager:
        return self._core_mgr

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
