from textual.app import App

from fit_ctf.ctf_base import CTFBase
from fit_ctf_rendezvous.core_manager import CoreManager
from fit_ctf_rendezvous.screens.app_screen.app_screen import AppScreen
from fit_ctf_rendezvous.screens.login_screen.login_screen import LoginScreen


class RendezvousApp(App):

    TITLE = "FIT Rendezvous"

    def __init__(self, ctf_base: CTFBase, **kwargs):
        self.core_mgr = CoreManager(ctf_base)
        super().__init__(**kwargs)

    def on_login_submit(self) -> None:
        self.pop_screen()
        self.push_screen(AppScreen(self, self.on_logout))

    def on_logout(self) -> None:
        self.pop_screen()
        self.push_screen(LoginScreen(self, self.on_login_submit))

    def on_mount(self) -> None:
        self.push_screen(LoginScreen(self, self.on_login_submit))

    async def _shutdown(self) -> None:
        # NOTE: workaround
        if self.core_mgr.active_user is not None:
            await self.core_mgr.cleanup()
        return await super()._shutdown()
