from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal
from textual.widget import Widget
from textual.widgets import Button, Input, Label, ListItem, ListView, Rule

from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class SubmitSecretPage(Container, CoreWidget):

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
                    for prj in self.core_mgr.ctf_base.ue_mgr.get_enrolled_projects(
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
        input_widget = self.query_one("#secret-value-input", Input)
        list_view = self.query_one("#project-list-selected", ListView)
        if not list_view.highlighted_child:
            return
        # secret
        _ = input_widget.value
        # selected_prj
        _ = list_view.highlighted_child.query_one(Label)._content

        # TODO: validate secret and selected project
