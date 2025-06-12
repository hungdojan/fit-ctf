from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.reactive import Reactive, reactive
from textual.widget import Widget
from textual.widgets import Label, Markdown

from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.utils import get_resource_dir
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class WelcomePage(Container, CoreWidget):

    label_content: Reactive[str] = reactive("home")

    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        CoreWidget.__init__(self, owner_screen)
        Container.__init__(self, *children, **kwargs)
        self.border_title = "Welcome"
        self._markdown_text = None

    @property
    def markdown_text(self) -> str:
        if self._markdown_text is None:
            with open(get_resource_dir() / "welcome_page.md", "r") as f:
                self._markdown_text = f.read()
        return self._markdown_text

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Markdown(self.markdown_text)

    def watch_label_content(self, old_content: str, new_content: str) -> None:
        if old_content == new_content:
            return
        label = self.query_one("#display-label", Label)
        label.update(new_content)
