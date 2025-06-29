from jinja2 import Environment, FileSystemLoader
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widget import Widget
from textual.widgets import (
    Button,
    DataTable,
    Markdown,
    Rule,
    TabbedContent,
    TabPane,
)
from textual.worker import Worker, WorkerState

from fit_ctf_rendezvous.exceptions import FitRendezvousException, InconsistentState
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.utils import get_resource_dir
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class ProjectInfoPage(Container, CoreWidget):

    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        Container.__init__(self, *children, **kwargs)
        CoreWidget.__init__(self, owner_screen)
        self.border_title = "Project Info"

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Manage instance"):
                with VerticalScroll():
                    yield Markdown(self.generate_ssh_help())
                yield Rule(line_style="ascii")
                yield Button(
                    "Start/Stop Instance", id="projectinfo-toggle-instance-btn"
                )
            with TabPane("Project Info"):
                with VerticalScroll():
                    yield Markdown("# Task description")
            with TabPane("Leaderboard"):
                with VerticalScroll():
                    yield self.generate_leaderboard()

    def generate_leaderboard(self) -> DataTable:
        table = DataTable()
        # TODO:
        columns = ("No.", "Username", "Score")
        table.add_columns(*columns)
        return table

    def generate_ssh_help(self) -> str:
        loader = FileSystemLoader(get_resource_dir() / "en")
        env = Environment(loader=loader)
        template = env.get_template("run_cluster_instruction.md.j2")
        try:
            port = self._get_port()
        except FitRendezvousException as e:
            self.core_mgr.ctf_base.logger.error(str(e))
            return "**Error occurred. Please contact the supervisor.**"
        return template.render(port=port)

    def _get_port(self) -> int:
        if not self.active_user or not self.core_mgr.selected_project:
            raise InconsistentState("Missing active user or project is not selected.")
        user_enrollment = self.core_mgr.ctf_base.ue_mgr.get_user_enrollment(
            self.active_user, self.core_mgr.selected_project
        )
        if not user_enrollment:
            raise InconsistentState(
                f"User {self.active_user.username} is not enrolled "
                "in {self.core_mgr.selected_project.name}."
            )
        return user_enrollment.forwarded_port

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
            btn = self.query_one("#projectinfo-toggle-instance-btn", Button)
            btn.disabled = True
        else:
            self.notify("Instance is shutting down...", severity="warning", timeout=3)
            self.run_worker(
                self.core_mgr.stop_user_instance(),
                name="toggle-instance-off",
                exclusive=True,
            )
            btn = self.query_one("#projectinfo-toggle-instance-btn", Button)
            btn.disabled = True

    @on(Worker.StateChanged)
    def worker_handler(self, event: Worker.StateChanged):
        if event.worker.state != WorkerState.SUCCESS:
            return
        if event.worker.name not in {"toggle-instance-on", "toggle-instance-off"}:
            return

        if event.worker.name == "toggle-instance-on":
            self.notify("Instance has started.", timeout=3)
            btn = self.query_one("#projectinfo-toggle-instance-btn", Button)
            btn.disabled = False
        elif event.worker.name == "toggle-instance-off":
            self.notify("Instance has shut down...", timeout=3)
            btn = self.query_one("#projectinfo-toggle-instance-btn", Button)
            btn.disabled = False
