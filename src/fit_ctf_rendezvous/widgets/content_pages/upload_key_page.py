from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Markdown, Rule

from fit_ctf_rendezvous.exceptions import InvalidAction
from fit_ctf_rendezvous.i18n import read_locale_markdown, tr
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class UploadKeyPage(Container, CoreWidget):
    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        Container.__init__(self, *children, **kwargs)
        CoreWidget.__init__(self, owner_screen)
        self.border_title = tr("upload_key.border")
        self._markdown_text = None

    @property
    def markdown_text(self) -> str:
        if self._markdown_text is None:
            self._markdown_text = read_locale_markdown("upload_key.md")
        return self._markdown_text

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Markdown(self.markdown_text)
        with Center():
            yield Rule(line_style="ascii")
        with Horizontal():
            yield Label(tr("upload_key.public_key"))
            yield Input(placeholder=tr("upload_key.placeholder"), id="key-value-input")
        with Center():
            yield Button(tr("upload_key.button"), id="upload-key-btn")

    @on(Button.Pressed, "#upload-key-btn")
    def upload_key_handler(self):
        key_input = self.query_one("#key-value-input", Input)
        # key value
        key_bytes = key_input.value.strip().encode()
        try:
            self.core_mgr.upload_public_key(key_bytes)
            self.notify(tr("upload_key.notify_success"))
        except InvalidAction as e:
            self.notify(tr("upload_key.notify_fail", error=str(e)), severity="error")
