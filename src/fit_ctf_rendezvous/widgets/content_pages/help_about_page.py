from rich.markdown import Markdown as RichMarkdown
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widget import Widget
from textual.widgets import Static

from fit_ctf_rendezvous.i18n import read_locale_markdown, tr
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class HelpAboutPage(Container, CoreWidget):
    """Static help copy using Rich Markdown (avoids Textual ``Markdown`` link/style issues)."""

    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        Container.__init__(self, *children, **kwargs)
        CoreWidget.__init__(self, owner_screen)

        self.border_title = tr("help_about.border")
        self._markdown_text: str | None = None

    @property
    def markdown_text(self) -> str:
        if self._markdown_text is None:
            self._markdown_text = read_locale_markdown("help_about_page.md")
        return self._markdown_text

    def compose(self) -> ComposeResult:
        # hyperlinks=False: Rich link styles confuse Textual's renderer (freeze / marshal errors).
        # markup=False on Static: content is already a Rich renderable, not console markup.
        with VerticalScroll():
            yield Static(
                RichMarkdown(self.markdown_text, hyperlinks=False),
                id="help-about-md",
                markup=False,
            )
