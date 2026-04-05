from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widget import Widget
from textual.widgets import Markdown

from fit_ctf_rendezvous.components.rendezvous_logger import RendezvousLogger
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class ShowConsolePage(Container, CoreWidget):

    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        Container.__init__(self, *children, **kwargs)
        CoreWidget.__init__(self, owner_screen)
        self.border_title = "Activity log"

    def compose(self) -> ComposeResult:
        logger = self.core_mgr.ctf_base.logger
        with VerticalScroll():
            if isinstance(logger, RendezvousLogger):
                yield Markdown(
                    "Backend messages and errors appear below while this page is open. "
                    "The log keeps at most the last 1000 lines."
                )
                yield logger
            else:
                yield Markdown(
                    "## Activity log\n\n"
                    "Live log output is only available when running the full "
                    "`fit-rendezvous` entrypoint (in-app logger). "
                    "Tests and embedded uses keep the default file/stdout logger."
                )
