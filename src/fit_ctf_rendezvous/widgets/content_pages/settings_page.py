from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.widget import Widget
from textual.widgets import Label, Markdown, Rule, Select, Switch

from fit_ctf_rendezvous.i18n import i18n, tr
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class SettingsPage(Container, CoreWidget):
    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        Container.__init__(self, *children, **kwargs)
        CoreWidget.__init__(self, owner_screen)
        self.border_title = tr("settings.border")

    def compose(self) -> ComposeResult:
        yield Markdown(tr("settings.heading"))
        yield Markdown(tr("settings.theme_hint"))
        with Horizontal():
            yield Label(tr("settings.dark_theme"))
            yield Switch(
                value=self.owner_screen.app.current_theme.dark,
                id="settings-dark-switch",
            )
        yield Rule(line_style="ascii")
        yield Markdown(tr("settings.language_hint"))
        with Horizontal():
            yield Label(tr("settings.language"))
            yield Select(
                [(tr("settings.lang_en"), "en"), (tr("settings.lang_cs"), "cs")],
                value=i18n.locale,
                id="settings-language-select",
                allow_blank=False,
            )

    @on(Switch.Changed, "#settings-dark-switch")
    def dark_changed(self, event: Switch.Changed) -> None:
        self.owner_screen.app.theme = "textual-dark" if event.switch.value else "textual-light"
        self.owner_screen.app.persist_rendezvous_user_settings()

    @on(Select.Changed, "#settings-language-select")
    def language_changed(self, event: Select.Changed) -> None:
        val = event.value
        if val == Select.BLANK:
            return
        code = str(val)
        if code == i18n.locale:
            return
        i18n.locale = code
        self.owner_screen.app.persist_rendezvous_user_settings()
        from fit_ctf_rendezvous.screens.app_screen.app_screen import AppScreen

        screen = self.owner_screen
        if isinstance(screen, AppScreen):
            screen.schedule_locale_rebuild()
