from textual.app import ComposeResult
from textual.containers import Container
from textual.reactive import Reactive, reactive
from textual.widget import Widget
from textual.widgets import Label

from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class AppContentContainer(Container, CoreWidget):

    label_content: Reactive[str] = reactive("home")

    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        CoreWidget.__init__(self, owner_screen)
        Container.__init__(self, *children, **kwargs)

    def compose(self) -> ComposeResult:
        yield Label(self.label_content, id="display-label")
        yield Label(self.label_content)
        yield Label(self.label_content)
        yield Label(self.label_content)

    def watch_label_content(self, old_content: str, new_content: str) -> None:
        if old_content == new_content:
            return
        label = self.query_one("#display-label", Label)
        label.update(new_content)
