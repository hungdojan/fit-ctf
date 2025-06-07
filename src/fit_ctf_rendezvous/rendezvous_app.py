from typing import Type

from textual.app import App
from textual.driver import Driver
from textual.types import CSSPathType

from fit_ctf_backend.ctf_manager import CTFManager
from fit_ctf_rendezvous.screens.login_screen.login_screen import LoginScreen


class RendezvousApp(App):

    TITLE = "Rendezvous"
    SCREENS = {"LoginScreen": LoginScreen}

    def __init__(
        self,
        ctf_mgr: CTFManager,
        driver_class: Type[Driver] | None = None,
        css_path: CSSPathType | None = None,
        watch_css: bool = False,
        ansi_color: bool = False,
    ):
        self.ctf_mgr = ctf_mgr
        super().__init__(driver_class, css_path, watch_css, ansi_color)

    def on_mount(self) -> None:
        self.push_screen("LoginScreen")
