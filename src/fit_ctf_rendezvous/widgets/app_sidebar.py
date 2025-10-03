from typing import Callable

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Container, VerticalScroll
from textual.reactive import Reactive, reactive
from textual.widget import Widget
from textual.widgets import Button, Label, Rule

from fit_ctf_models.project import Project
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class AppSideBar(Container, CoreWidget):

    selected_project: Reactive[Project | None] = reactive(None)

    def __init__(
        self,
        owner_screen: BaseScreen,
        on_page_select: Callable[[str], None] = lambda _: None,
        *children: Widget,
        **kwargs,
    ):
        CoreWidget.__init__(self, owner_screen)
        Container.__init__(self, *children, **kwargs)
        self.on_page_select = on_page_select
        self.owner_screen.core_mgr.register_hook(
            "selected_project", __class__.__name__, self.selected_project_hook
        )
        self.label = Label(self._label_text(), id="label-project-name")

    def _label_text(self) -> str:
        return (
            "No project\nselected"
            if not self.selected_project
            else f"Project:\n{self.selected_project.name}"
        )

    def compose(self) -> ComposeResult:
        with Center():
            yield Button(f"Hello, {self.active_user.username}", id="sidebar-home-btn")
        # TODO: selected project
        with Center():
            yield Rule(line_style="ascii")
        with VerticalScroll():
            yield self.label
            yield Button(
                "Project Info",
                id="sidebar-project-info-btn",
                disabled=self.selected_project is None,
                classes="sidebar-active-btn",
            )
            yield Button(
                "Submit Secret",
                id="sidebar-submit-secret-btn",
            )
            # yield Button(
            #     "Show Console",
            #     id="sidebar-show-console-btn",
            #     disabled=self.selected_project is None,
            #     classes="sidebar-active-btn",
            # )
            yield Rule(line_style="ascii")
            yield Button("Select Project", id="sidebar-select-project-btn")
            yield Button("Upload public key", id="sidebar-upload-key-btn")
            # yield Button("Settings", id="sidebar-settings-btn")
            yield Button("About & Help", id="sidebar-help-about-btn")

        with Center():
            yield Rule(line_style="ascii")

        yield Button("Logout", variant="error", id="sidebar-logout-btn")

    def on_mount(self) -> None:
        self.set_interval(3, self.update_instance_status)

    async def update_instance_status(self) -> None:
        if self.selected_project is None:
            self.label.styles.background = "black"
            self.label.styles.color = "white"
        elif await self.core_mgr.instance_is_running():
            self.label.styles.background = "green"
            self.label.styles.color = "white"
        else:
            self.label.styles.background = "yellow"
            self.label.styles.color = "black"

    @on(Button.Pressed)
    def page_button_select(self, event: Button.Pressed):
        button_id = event.button.id
        if not button_id:
            return
        # remove prefix `sidebar-` and suffix `-btn`
        page_name = button_id[8:-4]
        self.on_page_select(page_name)

    def watch_selected_project(
        self, old_project: Project | None, new_project: Project | None
    ) -> None:
        if old_project == new_project:
            return

        for button in self.query(".sidebar-active-btn").results(Button):
            button.disabled = new_project is None
        self.label.update(self._label_text())

    def selected_project_hook(self, prj: Project | None):
        self.selected_project = prj
