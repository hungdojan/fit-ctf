from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widget import Widget
from textual.widgets import Markdown

from fit_ctf_rendezvous.i18n import read_locale_markdown, tr
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class WelcomePage(Container, CoreWidget):

    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        CoreWidget.__init__(self, owner_screen)
        Container.__init__(self, *children, **kwargs)
        self.border_title = tr("welcome.border")
        self._markdown_text: str | None = None

    @property
    def markdown_text(self) -> str:
        if self._markdown_text is None:
            self._markdown_text = read_locale_markdown("welcome_page.md")
        return self._markdown_text

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Markdown(self.markdown_text)
