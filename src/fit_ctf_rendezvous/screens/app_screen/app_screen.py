from typing import Callable

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, HorizontalGroup
from textual.worker import Worker, WorkerState

import fit_ctf_rendezvous.rendezvous_app as r_app
from fit_ctf_rendezvous.i18n import tr
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets import (
    AppSideBar,
    HelpAboutPage,
    ProjectInfoPage,
    ProjectSelector,
    SettingsPage,
    ShowLogsPage,
    SubmitSecretPage,
    UploadKeyPage,
    WelcomePage,
)
from fit_ctf_rendezvous.widgets.content_pages.change_password_page import (
    ChangePasswordPage,
)


class AppScreen(BaseScreen):
    CSS_PATH = "app_screen_styles.tcss"

    def __init__(
        self, base_app: "r_app.RendezvousApp", on_exit: Callable[[], None], **kwargs
    ) -> None:
        super().__init__(base_app, **kwargs)
        self.on_exit = on_exit
        self.page_state = "home"
        self._build_sidebar_and_pages()
        self.curr_content_widget = self.pages[self.page_state]

    def _build_sidebar_and_pages(self) -> None:
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
            "upload-key": UploadKeyPage(self, id="upload-key-page"),
            "help-about": HelpAboutPage(self, id="help-about-page"),
            "show-logs": ShowLogsPage(self, id="show-logs-page"),
            "settings": SettingsPage(self, id="settings-page"),
            "change-pswd": ChangePasswordPage(self, id="change-pswd-page"),
        }

    @property
    def horizontal_group(self) -> Container:
        return self.query_one("#content-container", Container)

    def page_selector_handler(self, page_name: str) -> None:
        """Schedule navigation; ``remove()`` must be awaited before ``mount()`` (Textual 3)."""
        self.run_worker(
            self._async_page_select(page_name),
            name="page-select",
            group="sidebar-nav",
            exclusive=True,
            exit_on_error=False,
        )

    async def _async_page_select(self, page_name: str) -> None:
        if self.page_state == page_name:
            return
        if page_name == "logout":
            if self.core_mgr.active_user is not None:
                logout_btn = self.side_bar.query_one("#sidebar-logout-btn")
                logout_btn.disabled = True
                self.notify(tr("app.cleanup"), severity="warning", timeout=3)
                self.run_worker(self.core_mgr.cleanup(), name="logout-cleanup")
            else:
                self.on_exit()
            return
        if page_name not in self.pages:
            return
        await self.curr_content_widget.remove()
        self.page_state = page_name
        await self.horizontal_group.mount(self.pages[self.page_state])
        self.curr_content_widget = self.pages[self.page_state]

    async def rebuild_ui_for_locale(self) -> None:
        """Recreate sidebar and all pages so ``tr()`` strings match the new locale."""
        saved = self.page_state
        hg = self.query_one("#app-main-layout", HorizontalGroup)
        for child in list(hg.children):
            await child.remove()
        self._build_sidebar_and_pages()
        self.page_state = saved
        self.curr_content_widget = self.pages[saved]
        await hg.mount(self.side_bar)
        content = Container(id="content-container")
        await hg.mount(content)
        await content.mount(self.curr_content_widget)
        self.side_bar.selected_project_hook(self.core_mgr.selected_project)

    def schedule_locale_rebuild(self) -> None:
        """Rebuild UI after the current event finishes.

        Must not call ``rebuild_ui_for_locale`` directly from ``Select.Changed`` on
        Settings: that would remove the widget tree while still inside its handler
        and freeze the app.
        """
        self.run_worker(
            self.rebuild_ui_for_locale(),
            name="locale-rebuild",
            exit_on_error=False,
        )

    def compose(self) -> ComposeResult:
        with HorizontalGroup(id="app-main-layout"):
            yield self.side_bar
            with Container(id="content-container"):
                yield self.curr_content_widget
        for i in super().compose():
            yield i

    @on(Worker.StateChanged)
    def worker_state_change(self, event: Worker.StateChanged):
        worker = event.worker
        if worker.name == "logout-cleanup":
            if worker.state == WorkerState.ERROR:
                logout_btn = self.side_bar.query_one("#sidebar-logout-btn")
                logout_btn.disabled = False
                err = worker.error
                self.notify(
                    str(err) if err else tr("app.cleanup_failed"),
                    severity="error",
                    timeout=5,
                )
                return
            if worker.state == WorkerState.SUCCESS:
                self.notify(tr("app.cleanup_done"), timeout=3)
                self.core_mgr.ctf_base.user_mgr.record_logout(self.core_mgr.active_user)
                self.core_mgr.active_user = None
                self.core_mgr.selected_project = None
                self.on_exit()
