from typing import Callable

from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, Label


class LoginDialog(Container):
    DEFAULT_CSS = """
    LoginDialog {
        align: center middle;
        width: auto;
        max-height: 9;
        max-width: 36;
        border: ascii white;
    }

    #login_title {
        align: center middle;
        margin: 0 0 1 0
    }

    #login_quit_button, #login_submit_button {
        border: none;
        min-width: 10;
    }

    .login_button:focus {
        border: none;
    }

    .login_input, .login_input:focus {
        height: 1;
        max-width: 20;
        padding: 0;
        border: none;
    }
    .login_label {
        height: 1;
        content-align: center middle;
        margin: 0 2 0 0
    }
    .form-row {
        margin: 0;
        padding: 0;
        align: center middle;
    }
    .form-button {
        align: center middle;
        margin: 1 0 0 0;
    }
    Checkbox, Checkbox:focus {
        border: none;
    }
    """

    def __init__(
        self,
        on_submit: Callable[[str, str], None],
        on_cancel: Callable[[], None],
        *children: Widget,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
        markup: bool = True
    ) -> None:
        super().__init__(
            *children,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
            markup=markup
        )
        self.on_submit = on_submit
        self.on_cancel = on_cancel

    def compose(self) -> ComposeResult:
        # yield Horizontal()
        with Center():
            yield Label("CTF Login", id="login_title")
        with Horizontal(classes="form-row"):
            yield Label("Username", classes="login_label")
            yield Input(
                placeholder="Username",
                id="login_input_username",
                classes="login_input",
            )
        with Horizontal(classes="form-row"):
            yield Label("Password", classes="login_label")
            yield Input(
                password=True,
                placeholder="Password",
                id="login_input_password",
                classes="login_input",
            )
        with Center():
            yield Checkbox("Show Password", id="login_checkbox")
        with Horizontal(classes="form-button"):
            yield Button(
                "Quit",
                variant="error",
                id="login_quit_button",
                classes="login_button",
            )
            yield Button(
                "Submit",
                variant="success",
                id="login_submit_button",
                classes="login_button",
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id

        if button_id == "login_quit_button":
            self.on_cancel()
        elif button_id == "login_submit_button":
            username_input = self.query_one("#login_input_username", Input)
            password_input = self.query_one("#login_input_password", Input)
            username, password = username_input.value, password_input.value
            self.on_submit(username, password)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        checkbox_id = event.checkbox.id

        if checkbox_id == "login_checkbox":
            input_element = self.query_one("#login_input_password", Input)
            input_element.password = not event.checkbox.value
