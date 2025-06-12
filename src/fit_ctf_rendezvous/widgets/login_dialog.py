from typing import Callable

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, Label, Rule

from fit_ctf_rendezvous.exceptions import FitRendezvousException
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class LoginDialog(Container, CoreWidget):

    def __init__(
        self,
        owner_screen: BaseScreen,
        on_submit: Callable[[str, str], None],
        on_cancel: Callable[[], None],
        *children: Widget,
        **kwargs
    ) -> None:
        CoreWidget.__init__(self, owner_screen)
        Container.__init__(self, *children, **kwargs)

        self.on_submit = on_submit
        self.on_cancel = on_cancel

    def compose(self) -> ComposeResult:
        with Center():
            yield Label("CTF Login")
        with Center():
            yield Rule(line_style="ascii")
        with Horizontal():
            yield Label("Username")
            yield Input(
                placeholder="Username",
                id="login-username-input",
                # FIX: remove
                value="user1",
            )
        with Horizontal():
            yield Label("Password")
            yield Input(
                password=True,
                placeholder="Password",
                id="login-password-input",
                # FIX: remove
                value="BlackUnicorn12",
            )
        with Center():
            yield Checkbox("Show Password", id="login-checkbox")
        with Center():
            yield Label("", id="login-message-label")
        with Center():
            yield Rule(line_style="ascii")
        with Horizontal():
            yield Button(
                "Quit",
                variant="error",
                id="login-quit-btn",
            )
            yield Button(
                "Submit",
                variant="success",
                id="login-submit-btn",
            )

    @on(Button.Pressed, "#login-quit-btn")
    def quit_btn_handler(self):
        self.on_cancel()

    @on(Button.Pressed, "#login-submit-btn")
    def action_submit_btn_handler(self):
        username_input = self.query_one("#login-username-input", Input)
        password_input = self.query_one("#login-password-input", Input)
        username, password = username_input.value, password_input.value
        try:
            self.on_submit(username, password)
        except FitRendezvousException as e:
            label = self.query_one("#login-message-label", Label)
            label.styles.visibility = "visible"
            label.update(str(e))

    @on(Checkbox.Changed, "#login-checkbox")
    def show_password_handler(self, event: Checkbox.Changed) -> None:
        input_element = self.query_one("#login-input-password", Input)
        input_element.password = not event.checkbox.value
