from typing import Callable

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Container, VerticalScroll
from textual.reactive import Reactive, reactive
from textual.widget import Widget
from textual.widgets import Button, Label, Rule

from fit_ctf_models.project import Project
from fit_ctf_rendezvous.i18n import tr
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
        if not self.selected_project:
            return tr("sidebar.no_project")
        return f"{self.selected_project.name}\n{tr('sidebar.project_status_hint')}"

    def compose(self) -> ComposeResult:
        with Center():
            yield Button(
                tr("sidebar.hello", username=self.active_user.username),
                id="sidebar-home-btn",
            )
            yield self.label
        with Center():
            yield Rule(line_style="ascii")
        with VerticalScroll():
            yield Button(
                tr("sidebar.select_project"),
                id="sidebar-select-project-btn",
            )
            yield Button(
                tr("sidebar.submit_secret"),
                id="sidebar-submit-secret-btn",
            )
            yield Rule(line_style="ascii")
            yield Button(
                tr("sidebar.project_info"),
                id="sidebar-project-info-btn",
                disabled=self.selected_project is None,
                classes="sidebar-active-btn",
            )
            yield Rule(line_style="ascii")
            yield Button(tr("sidebar.change_password"), id="sidebar-change-pswd-btn")
            yield Button(tr("sidebar.upload_key"), id="sidebar-upload-key-btn")
            yield Button(tr("sidebar.about_help"), id="sidebar-help-about-btn")
            yield Button(tr("sidebar.show_logs"), id="sidebar-show-logs-btn")
            yield Button(tr("sidebar.settings"), id="sidebar-settings-btn")

        with Center():
            yield Rule(line_style="ascii")

        yield Button(tr("sidebar.logout"), variant="error", id="sidebar-logout-btn")

    def on_mount(self) -> None:
        self.set_interval(3, self.update_instance_status)

    def on_unmount(self) -> None:
        self.core_mgr.unregister_hook("selected_project", self.__class__.__name__)

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
