from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widget import Widget
from textual.widgets import Label, Markdown, Switch

from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class SettingsPage(Container, CoreWidget):

    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        Container.__init__(self, *children, **kwargs)
        CoreWidget.__init__(self, owner_screen)
        self.border_title = "Settings"

    def compose(self) -> ComposeResult:
        yield Markdown("## Settings")
        yield Markdown("Theme applies to this session only.")
        with Horizontal():
            yield Label("Dark theme")
            yield Switch(
                value=self.owner_screen.app.current_theme.dark,
                id="settings-dark-switch",
            )

    @on(Switch.Changed, "#settings-dark-switch")
    def dark_changed(self, event: Switch.Changed) -> None:
        self.owner_screen.app.theme = (
            "textual-dark" if event.switch.value else "textual-light"
        )
