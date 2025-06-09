from fit_ctf_rendezvous.screens.base_screen import BaseScreen


class CoreWidget:

    def __init__(self, owner_screen: BaseScreen) -> None:
        self._owner_screen = owner_screen

    @property
    def owner_screen(self):
        return self._owner_screen
