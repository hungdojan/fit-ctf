from typing import Callable

from textual.app import ComposeResult

import fit_ctf_rendezvous.rendezvous_app as r_app
from fit_ctf_rendezvous.exceptions import IncorrectCredentials
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets import LoginDialog


class LoginScreen(BaseScreen):
    CSS_PATH = "login_screen_styles.tcss"

    def __init__(
        self, base_app: "r_app.RendezvousApp", on_exit: Callable[[], None], **kwargs
    ) -> None:
        super().__init__(base_app, **kwargs)
        self.on_exit = on_exit

    def on_submit(self, username: str, password: str):
        result = self.core_mgr.validate_login(username, password)
        if not result:
            raise IncorrectCredentials("Incorrect login credentials!")
        self.on_exit()

    def compose(self) -> ComposeResult:
        yield LoginDialog(self, self.on_submit, lambda: self.app.exit())
        for i in super().compose():
            yield i
