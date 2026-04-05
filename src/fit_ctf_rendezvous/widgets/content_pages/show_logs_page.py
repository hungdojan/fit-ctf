from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widget import Widget
from textual.widgets import Log, Markdown

from fit_ctf_rendezvous.i18n import tr
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class ShowLogsPage(Container, CoreWidget):
    """Live backend log lines (thread-safe buffer, drained on the main thread)."""

    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        Container.__init__(self, *children, **kwargs)
        CoreWidget.__init__(self, owner_screen)
        self.border_title = tr("show_logs.border")

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Markdown(tr("show_logs.intro"))
            yield Log(
                id="tui-show-logs",
                max_lines=2000,
                auto_scroll=True,
            )
