from fit_ctf.models.core.user import User
from fit_ctf_rendezvous.core_manager import CoreManager
from fit_ctf_rendezvous.exceptions import UserNotLoggedIn
from fit_ctf_rendezvous.i18n import tr
from fit_ctf_rendezvous.screens.base_screen import BaseScreen


class CoreWidget:

    def __init__(self, owner_screen: BaseScreen) -> None:
        self._owner_screen = owner_screen

    @property
    def owner_screen(self):
        return self._owner_screen

    @property
    def core_mgr(self) -> CoreManager:
        return self._owner_screen.core_mgr

    @property
    def active_user(self) -> User:
        user = self.core_mgr.active_user
        if not user:
            raise UserNotLoggedIn(tr("core.not_logged_in"))
        return user

    def cleanup_registry(self):
        self.owner_screen.core_mgr.unregister_from_all(self.__class__.__name__)
