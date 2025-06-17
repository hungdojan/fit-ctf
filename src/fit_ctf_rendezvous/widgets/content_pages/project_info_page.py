from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widget import Widget
from textual.widgets import Button, DataTable, Markdown, Rule, TabbedContent, TabPane
from textual.worker import Worker, WorkerState

from fit_ctf_rendezvous.components.rendezvous_logger import RendezvousLogger
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class ProjectInfoPage(Container, CoreWidget):

    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        Container.__init__(self, *children, **kwargs)
        CoreWidget.__init__(self, owner_screen)
        self.border_title = "Project Info"

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Manage instance"):
                yield RendezvousLogger(self.owner_screen.core_mgr.ctf_base)
                yield Rule(line_style="ascii")
                yield Button(
                    "Start/Stop Instance", id="projectinfo-toggle-instance-btn"
                )
            with TabPane("Project Info"):
                with VerticalScroll():
                    yield Markdown("test2")
            with TabPane("Leaderboard"):
                with VerticalScroll():
                    yield self.generate_leaderboard()

    def generate_leaderboard(self) -> DataTable:
        table = DataTable()
        # TODO:
        columns = ("No.", "Username", "Score")
        table.add_columns(*columns)
        return table

    @on(Button.Pressed, "#projectinfo-toggle-instance-btn")
    async def toggle_instance(self):
        # TODO: make it more efficient
        if not await self.core_mgr.instance_is_running():
            self.notify("Instance is booting...", severity="warning", timeout=3)
            self.run_worker(
                self.core_mgr.start_user_instance(),
                name="toggle-instance-on",
                exclusive=True,
            )
        else:
            self.notify("Instance is shutting down...", severity="warning", timeout=3)
            self.run_worker(
                self.core_mgr.stop_user_instance(),
                name="toggle-instance-off",
                exclusive=True,
            )

    @on(Worker.StateChanged)
    def worker_handler(self, event: Worker.StateChanged):
        if event.worker.state == WorkerState.SUCCESS:
            if event.worker.name == "toggle-instance-on":
                self.notify("Instance has started.", timeout=3)
            elif event.worker.name == "toggle-instance-off":
                self.notify("Instance has shut down...", timeout=3)
