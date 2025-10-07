from textual import on
from textual.app import ComposeResult
from textual.containers import Center, Container, Horizontal, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Markdown, Rule

from fit_ctf_rendezvous.exceptions import InvalidAction
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.utils import get_resource_dir
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class UploadKeyPage(Container, CoreWidget):

    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        Container.__init__(self, *children, **kwargs)
        CoreWidget.__init__(self, owner_screen)
        self.border_title = "Upload Key"
        self._markdown_text = None

    @property
    def markdown_text(self) -> str:
        if self._markdown_text is None:
            with open(get_resource_dir() / "en" / "upload_key.md", "r") as f:
                self._markdown_text = f.read()
        return self._markdown_text

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Markdown(self.markdown_text)
        with Center():
            yield Rule(line_style="ascii")
        with Horizontal():
            yield Label("Public key: ")
            yield Input(placeholder="Public key value", id="key-value-input")
        with Center():
            yield Button("Upload Key", id="upload-key-btn")

    @on(Button.Pressed, "#upload-key-btn")
    def upload_key_handler(self):
        key_input = self.query_one("#key-value-input", Input)
        # key value
        key_bytes = key_input.value.strip().encode()
        try:
            self.core_mgr.upload_public_key(key_bytes)
            self.notify("Key successfully uploaded")
        except InvalidAction as e:
            self.notify(f"Uploading key failed: {str(e)}", severity="error")
