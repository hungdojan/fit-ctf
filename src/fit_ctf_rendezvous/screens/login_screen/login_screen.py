from textual.app import ComposeResult
from textual.screen import Screen

from fit_ctf_rendezvous.widgets.login_dialog import LoginDialog


class LoginScreen(Screen):
    CSS_PATH = "login_screen_styles.tcss"

    def on_submit(self, username: str, password: str):
        # TODO:
        pass

    def compose(self) -> ComposeResult:
        yield LoginDialog(self.on_submit, lambda: self.app.exit())
