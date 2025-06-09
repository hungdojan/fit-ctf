from typing import Callable

from textual.app import ComposeResult

from fit_ctf_rendezvous.core_manager import CoreManager
from fit_ctf_rendezvous.exceptions import IncorrectCredentials
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.login_dialog import LoginDialog


class LoginScreen(BaseScreen):
    CSS_PATH = "login_screen_styles.tcss"

    def __init__(
        self, core_mgr: CoreManager, on_exit: Callable[[], None], **kwargs
    ) -> None:
        super().__init__(core_mgr, **kwargs)
        self.on_exit = on_exit

    def on_submit(self, username: str, password: str):
        result = self.core_mgr.check_login(username, password)
        if not result:
            raise IncorrectCredentials("Incorrect login credentials!")
        self.on_exit()

    def compose(self) -> ComposeResult:
        yield LoginDialog(self, self.on_submit, lambda: self.app.exit())
        for i in super().compose():
            yield i
