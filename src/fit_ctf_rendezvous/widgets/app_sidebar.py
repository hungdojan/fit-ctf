from typing import Callable

from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Container, VerticalScroll
from textual.reactive import Reactive, reactive
from textual.widget import Widget
from textual.widgets import Button, Rule

from fit_ctf_models.user import User
from fit_ctf_rendezvous.exceptions import UserNotLoggedIn
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class AppSideBar(Container, CoreWidget):

    selected_project: Reactive[str | None] = reactive(None)

    def __init__(
        self,
        owner_screen: BaseScreen,
        on_home: Callable[[], None] = lambda: None,
        on_select_project: Callable[[], None] = lambda: None,
        on_start_instance: Callable[[], None] = lambda: None,
        on_stop_instance: Callable[[], None] = lambda: None,
        on_show_stats: Callable[[], None] = lambda: None,
        on_upload_key: Callable[[], None] = lambda: None,
        on_about_help: Callable[[], None] = lambda: None,
        on_settings: Callable[[], None] = lambda: None,
        on_logout: Callable[[], None] = lambda: None,
        *children: Widget,
        **kwargs,
    ):
        CoreWidget.__init__(self, owner_screen)
        Container.__init__(self, *children, **kwargs)
        self.on_home = on_home
        self.on_select_project = on_select_project
        self.on_start_instance = on_start_instance
        self.on_stop_instance = on_stop_instance
        self.on_show_stats = on_show_stats
        self.on_upload_key = on_upload_key
        self.on_about_help = on_about_help
        self.on_settings = on_settings
        self.on_logout = on_logout

    @property
    def active_user(self) -> User:
        user = self.owner_screen.core_mgr.user
        if not user:
            raise UserNotLoggedIn("User is not logged in!")
        return user

    def compose(self) -> ComposeResult:
        with Center():
            yield Button(f"Hello, {self.active_user.username}", id="sidebar-home-btn")
        # TODO: selected project
        with Center():
            yield Rule(line_style="ascii")
        with VerticalScroll():
            yield Button("Select Project", id="sidebar-select-project-btn")
            yield Rule(line_style="ascii")
            yield Button(
                "Start Instance",
                id="sidebar-start-btn",
                disabled=self.selected_project is None,
            )
            yield Button(
                "Show stats",
                id="sidebar-stats-btn",
                disabled=self.selected_project is None,
            )
            yield Button(
                "Stop Instance",
                id="sidebar-stop-btn",
                disabled=self.selected_project is None,
            )
            yield Rule(line_style="ascii")
            yield Button("Upload public key", id="sidebar-upload-key-btn")
            yield Button("About & Help", id="sidebar-about-help-btn")
            yield Button("Settings", id="sidebar-settings-btn")

        yield Button("Logout", variant="error", id="sidebar-logout-btn")

    @on(Button.Pressed, "#sidebar-home-btn")
    def action_home(self) -> None:
        self.on_home()

    @on(Button.Pressed, "#sidebar-select-project-btn")
    def action_select_project(self) -> None:
        self.on_select_project()

    @on(Button.Pressed, "#sidebar-start-btn")
    def action_start_instance(self) -> None:
        self.on_start_instance()

    @on(Button.Pressed, "#sidebar-stats-btn")
    def action_show_stats(self) -> None:
        self.on_show_stats()

    @on(Button.Pressed, "#sidebar-stop-btn")
    def action_stop_instance(self) -> None:
        self.on_stop_instance()

    @on(Button.Pressed, "#sidebar-upload-key-btn")
    def action_upload_keu(self) -> None:
        self.on_upload_key()

    @on(Button.Pressed, "#sidebar-about-help-btn")
    def action_about_help(self) -> None:
        self.on_about_help()

    @on(Button.Pressed, "#sidebar-settings-btn")
    def action_settings(self) -> None:
        self.on_settings()

    @on(Button.Pressed, "#sidebar-logout-btn")
    def action_logout(self) -> None:
        self.on_logout()
