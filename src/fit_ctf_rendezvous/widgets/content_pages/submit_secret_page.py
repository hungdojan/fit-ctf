import asyncio
from typing import cast

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Rule, Select

from fit_ctf_rendezvous.exceptions import FitRendezvousException
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class SubmitSecretPage(Container, CoreWidget):

    DISABLE_BUTTON_DELAY = 5

    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        Container.__init__(self, *children, **kwargs)
        CoreWidget.__init__(self, owner_screen)
        self.border_title = "Submit Secret"
        self._selected_project_name = ""

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("Secret value: ")
            yield Input(placeholder="Secret", id="secret-value-input")
        with Horizontal():
            yield Label("Project: ")
            assert self.core_mgr.active_user is not None
            yield Select(
                options=(
                    (prj.name, prj.name)
                    for prj in self.core_mgr.ctf_base.ue_mgr.get_enrolled_projects(
                        self.core_mgr.active_user
                    )
                ),
                id="project-select",
            )
        with Center():
            yield Rule(line_style="ascii")
        with Center():
            yield Button("Validate", id="validate-secret-btn", variant="primary")

    @on(Select.Changed, "#project-select")
    def project_select_handler(self, event: Select.Changed):
        self._selected_project_name = cast(
            str, event.value if event.value != Select.BLANK else ""
        )

    @on(Button.Pressed, "#validate-secret-btn")
    def validate_button_handler(self):
        """Define action after submit button is pressed."""
        if not self._selected_project_name:
            self.notify("Project not selected.", severity="error")
            return

        input_widget = self.query_one("#secret-value-input", Input)
        # secret
        secret_value = input_widget.value

        try:
            self.core_mgr.submit_secret(secret_value, self._selected_project_name)
            self.notify(
                "Secret successfully submitted", timeout=3, severity="information"
            )
        except FitRendezvousException as e:
            self.notify(str(e), timeout=3, severity="error")
            # to prevent secret brute-forcing
            # button will be disabled for few seconds if failed
            button = self.query_one("#validate-secret-btn", Button)
            button.disabled = True
            self.run_worker(
                self.reenable_submit_button(button), name="temporary-button-disable"
            )

    async def reenable_submit_button(self, button: Button):
        """Disable a button to prevent brute-forcing."""
        await asyncio.sleep(self.DISABLE_BUTTON_DELAY)
        button.disabled = False
