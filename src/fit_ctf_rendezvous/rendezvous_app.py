from textual.app import App
from textual.css.query import NoMatches
from textual.widgets import Log

from fit_ctf.ctf_base import CTFBase
from fit_ctf_rendezvous.rendezvous_core import RendezvousCore
from fit_ctf_rendezvous.screens.app_screen.app_screen import AppScreen
from fit_ctf_rendezvous.screens.login_screen.login_screen import LoginScreen
from fit_ctf_rendezvous.tui_log_sink import TuiLogSink


class RendezvousApp(App):
    TITLE = "FIT Rendezvous"

    def __init__(self, ctf_base: CTFBase, **kwargs):
        self.core_mgr = RendezvousCore(ctf_base)
        self._tui_log_sink = TuiLogSink()
        super().__init__(**kwargs)

    def on_login_submit(self) -> None:
        user = self.core_mgr.active_user
        if user is None:
            return
        from fit_ctf_rendezvous.user_rendezvous_settings import apply_to_app, load

        apply_to_app(self, load(self.core_mgr.ctf_base.paths, user))
        self.pop_screen()
        self.push_screen(AppScreen(self, self.on_logout))

    def on_logout(self) -> None:
        from fit_ctf_rendezvous.i18n import reset_locale_cache

        reset_locale_cache()
        self.pop_screen()
        self.push_screen(LoginScreen(self, self.on_login_submit))

    def persist_rendezvous_user_settings(self) -> None:
        """Save theme and locale for ``active_user`` (no-op if not logged in)."""
        u = self.core_mgr.active_user
        if u is None:
            return
        from fit_ctf_rendezvous.i18n import i18n
        from fit_ctf_rendezvous.user_rendezvous_settings import (
            RendezvousUserSettings,
            save,
        )

        save(
            self.core_mgr.ctf_base.paths,
            u,
            RendezvousUserSettings.create(
                locale=i18n.locale,
                dark_theme=self.current_theme.dark,
            ),
        )

    def on_mount(self) -> None:
        self._tui_log_sink.attach()
        self.set_interval(0.05, self._pump_tui_log_lines)
        self.push_screen(LoginScreen(self, self.on_login_submit))

    def _pump_tui_log_lines(self) -> None:
        try:
            log_w = self.query_one("#tui-show-logs", Log)
        except NoMatches:
            return
        for line in self._tui_log_sink.drain_for_widget():
            log_w.write_line(line)

    async def _shutdown(self) -> None:
        if self.core_mgr.active_user is not None:
            await self.core_mgr.cleanup()
            self.core_mgr.ctf_base.user_mgr.record_logout(self.core_mgr.active_user)
            self.core_mgr.active_user = None
            self.core_mgr.selected_project = None
        res = await super()._shutdown()
        self._tui_log_sink.detach()
        return res
