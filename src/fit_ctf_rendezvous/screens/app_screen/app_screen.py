from typing import Callable

from textual.app import ComposeResult
from textual.containers import HorizontalGroup
from textual.widgets import Button

from fit_ctf_rendezvous.core_manager import CoreManager
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.app_content_container import AppContentContainer
from fit_ctf_rendezvous.widgets.app_sidebar import AppSideBar


class AppScreen(BaseScreen):
    CSS_PATH = "app_screen_styles.tcss"

    def __init__(
        self, core_mgr: CoreManager, on_exit: Callable[[], None], **kwargs
    ) -> None:
        super().__init__(core_mgr, **kwargs)
        self.on_exit = on_exit
        self.app_content_container = AppContentContainer(
            self, id="app-content-container"
        )

    def logout_handler(self) -> None:
        # TODO: logout
        self.on_exit()

    def home_handler(self) -> None:
        self.app_content_container.label_content = "home"

    def upload_key_handler(self) -> None:
        self.app_content_container.remove_children()
        self.app_content_container.mount(Button("test"))

    def settings_handler(self) -> None:
        self.app_content_container.label_content = "settings"

    def about_help_handler(self) -> None:
        self.app_content_container.label_content = "about & help"

    def compose(self) -> ComposeResult:
        with HorizontalGroup():
            yield AppSideBar(
                self,
                on_home=self.home_handler,
                on_upload_key=self.upload_key_handler,
                on_settings=self.settings_handler,
                on_about_help=self.about_help_handler,
                on_logout=self.logout_handler,
            )
            yield self.app_content_container
        for i in super().compose():
            yield i
