from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Container, Grid, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Rule

from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class ProjectSelector(Container, CoreWidget):

    def __init__(
        self,
        owner_screen: BaseScreen,
        *children: Widget,
        **kwargs,
    ) -> None:
        Container.__init__(self, *children, **kwargs)
        CoreWidget.__init__(self, owner_screen)

    def compose(self) -> ComposeResult:
        self.border_title = "Select Project"
        with VerticalScroll():
            with Grid():
                for prj in self.core_mgr.get_active_projects():
                    yield Button(
                        prj.name, id=f"select-btn-{prj.name}", variant="primary"
                    )
        with Center():
            yield Rule(line_style="ascii")
        with Center():
            yield Button("Deselect", variant="warning", id="select-btn-deselect")

    @on(Button.Pressed)
    def button_handler(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if not button_id:
            return
        # remove prefix `select-btn-`
        cmd = button_id[11:]
        if cmd == "deselect":
            self.owner_screen.core_mgr.selected_project = None
        else:
            self.owner_screen.core_mgr.selected_project = (
                self.core_mgr.ctf_mgr.prj_mgr.get_project(cmd)
            )
