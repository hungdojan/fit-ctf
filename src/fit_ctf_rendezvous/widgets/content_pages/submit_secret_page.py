import asyncio

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal
from textual.widget import Widget
from textual.widgets import Button, Input, Label, ListItem, ListView, Rule

from fit_ctf_rendezvous.exceptions import FitRendezvousException
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class SubmitSecretPage(Container, CoreWidget):

    DISABLE_BUTTON_DELAY = 5

    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        Container.__init__(self, *children, **kwargs)
        CoreWidget.__init__(self, owner_screen)
        self.border_title = "Submit Secret"

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Label("Secret value: ")
            yield Input(placeholder="Secret", id="secret-value-input")
        with Horizontal():
            yield Label("Project: ")
            assert self.core_mgr.active_user is not None
            yield ListView(
                *[
                    ListItem(Label(prj.name))
                    for prj in self.core_mgr.ctf_base.user_enrollment_mgr.get_enrolled_projects(
                        self.core_mgr.active_user
                    )
                ],
                id="project-list-selected"
            )
        with Center():
            yield Rule(line_style="ascii")
        with Center():
            yield Button("Validate", id="validate-secret-btn", variant="primary")

    @on(Button.Pressed, "#validate-secret-btn")
    def validate_button_handler(self):
        """Define action after submit button is pressed."""
        input_widget = self.query_one("#secret-value-input", Input)
        list_view = self.query_one("#project-list-selected", ListView)
        if not list_view.highlighted_child:
            self.notify("Project not selected.")
            return
        # secret
        secret_value = input_widget.value
        # selected_prj
        project_name = str(list_view.highlighted_child.query_one(Label)._content)

        try:
            self.core_mgr.submit_secret(secret_value, project_name)
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
