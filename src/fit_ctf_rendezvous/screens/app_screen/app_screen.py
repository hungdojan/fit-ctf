from typing import Callable

from textual.app import ComposeResult
from textual.containers import Container, HorizontalGroup

import fit_ctf_rendezvous.rendezvous_app as r_app
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets import (
    AppSideBar,
    HelpAboutPage,
    ProjectInfoPage,
    ProjectSelector,
    SettingsPage,
    ShowConsolePage,
    SubmitSecretPage,
    UploadKeyPage,
    WelcomePage,
)


class AppScreen(BaseScreen):
    CSS_PATH = "app_screen_styles.tcss"

    def __init__(
        self, base_app: "r_app.RendezvousApp", on_exit: Callable[[], None], **kwargs
    ) -> None:
        super().__init__(base_app, **kwargs)
        self.on_exit = on_exit
        self.side_bar = AppSideBar(
            self, on_page_select=self.page_selector_handler, id="app-side-bar"
        )
        self.pages = {
            "home": WelcomePage(self, id="welcome-page"),
            "select-project": ProjectSelector(
                self,
                id="project-selector",
            ),
            "project-info": ProjectInfoPage(self, id="project-info-page"),
            "submit-secret": SubmitSecretPage(self, id="submit-secret-page"),
            "show-console": ShowConsolePage(self, id="show-console-page"),
            "upload-key": UploadKeyPage(self, id="upload-key-page"),
            "help-about": HelpAboutPage(self, id="help-about-page"),
            "settings": SettingsPage(self, id="settings-page"),
        }
        self.page_state = "home"
        self.curr_content_widget = self.pages[self.page_state]

    @property
    def horizontal_group(self) -> Container:
        return self.query_one("#content-container", Container)

    def page_selector_handler(self, page_name: str) -> None:
        self.curr_content_widget.remove()
        if page_name == "logout":
            self.core_mgr.active_user = None
            self.core_mgr.selected_project = None
            self.on_exit()
        elif page_name in self.pages.keys():
            self.page_state = page_name
            self.horizontal_group.mount(self.pages[self.page_state])
            self.curr_content_widget = self.pages[self.page_state]

    def compose(self) -> ComposeResult:
        with HorizontalGroup():
            yield self.side_bar
            with Container(id="content-container"):
                yield self.curr_content_widget
        for i in super().compose():
            yield i
