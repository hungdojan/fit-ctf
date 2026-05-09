from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header

import fit_ctf_rendezvous.rendezvous_app as r_app
from fit_ctf_rendezvous.rendezvous_core import RendezvousCore


class BaseScreen(Screen):
    def __init__(self, base_app: "r_app.RendezvousApp", **kwargs) -> None:
        super().__init__(**kwargs)
        self._base_app = base_app

    @property
    def core_mgr(self) -> RendezvousCore:
        return self._base_app.core_mgr

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
