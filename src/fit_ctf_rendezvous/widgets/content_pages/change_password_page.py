from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal, HorizontalScroll, Vertical
from textual.validation import Function
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, Label, Rule

from fit_ctf_rendezvous.exceptions import UserNotLoggedIn
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class ChangePasswordPage(Container, CoreWidget):

    DISABLE_BUTTON_DELAY = 5

    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        Container.__init__(self, *children, **kwargs)
        CoreWidget.__init__(self, owner_screen)
        self.border_title = "Submit Secret"
        self.allowed_object_ids = [
            "old-password",
            "new-password",
            "new-password-again",
        ]

    def compose(self) -> ComposeResult:
        with HorizontalScroll():
            with Vertical():
                with Horizontal():
                    yield Label("Old password: ")
                    yield Input(
                        id="old-password-input",
                        password=True,
                        validate_on=[],
                        validators=[
                            Function(
                                self.core_mgr.check_password_strength,
                                "Password is incorrect.",
                            )
                        ],
                        valid_empty=False,
                    )
                    yield Checkbox("show", id="show-old-password")
                with Horizontal():
                    yield Label("New Password: ")
                    yield Input(
                        id="new-password-input",
                        password=True,
                        validators=[
                            Function(
                                self.core_mgr.check_password_strength,
                                "Invalid format, requires at least 8 characters, one upper,"
                                "one lower character and a digit.",
                            )
                        ],
                        valid_empty=False,
                    )
                    yield Checkbox("show", id="show-new-password")
                with Horizontal():
                    yield Label("New Password (again): ")
                    yield Input(
                        id="new-password-again-input",
                        password=True,
                        validators=[
                            Function(
                                self.again_field_validator,
                                "New passwords do not match.",
                            )
                        ],
                        valid_empty=False,
                    )
                    yield Checkbox("show", id="show-new-password-again")
        with Center():
            yield Rule(line_style="ascii")
        with Center():
            yield Button("Change password", id="change-password-btn", variant="primary")

    def check_old_pswd(self, value: str) -> bool:
        if not self.core_mgr.active_user:
            raise UserNotLoggedIn("User not logged in.")
        return self.core_mgr.validate_login(self.core_mgr.active_user.username, value)

    def again_field_validator(self, value: str) -> bool:
        new_pswd_input = self.query_one("#new-password-input", Input)
        return new_pswd_input.value == value

    @on(Button.Pressed, "#change-password-btn")
    def validate_button_handler(self):
        values = {}
        for _id in self.allowed_object_ids:
            input = self.query_one(f"#{_id}-input", Input)
            result = input.validate(input.value)
            if not result:
                continue
            if not input.is_valid:
                # self.notify("Some fields are incorrect.", severity="error")
                self.notify(result.failure_descriptions[0], severity="warning")
                return
            values[_id] = input.value
        self.core_mgr.change_password(values["new-password"])
        self.notify("Password changed successfully.")
        for _id in self.allowed_object_ids:
            input = self.query_one(f"#{_id}-input", Input)
            input.value = ""

    @on(Checkbox.Changed)
    def show_pswd_checkbox_handler(self, event: Checkbox.Changed):
        checkbox = event.checkbox
        if (
            not checkbox.id
            or checkbox.id.removeprefix("show-") not in self.allowed_object_ids
        ):
            return

        core_id = checkbox.id.removeprefix("show-")
        input_elem = self.query_one(f"#{core_id}-input", Input)
        input_elem.password = not event.checkbox.value
