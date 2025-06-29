from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widget import Widget
from textual.widgets import Markdown

from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.utils import get_resource_dir
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class HelpAboutPage(Container, CoreWidget):

    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        Container.__init__(self, *children, **kwargs)
        CoreWidget.__init__(self, owner_screen)

        self.border_title = "About & Help"
        self._markdown_text = None

    @property
    def markdown_text(self) -> str:
        if self._markdown_text is None:
            with open(get_resource_dir() / "en" / "help_about_page.md", "r") as f:
                self._markdown_text = f.read()
        return self._markdown_text

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Markdown(self.markdown_text)
