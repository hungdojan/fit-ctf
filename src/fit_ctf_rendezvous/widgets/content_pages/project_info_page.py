from jinja2 import Environment
from rich.text import Text
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
from fit_ctf_rendezvous.i18n import jinja_resources_loader, tr
from fit_ctf_rendezvous.screens.base_screen import BaseScreen
from fit_ctf_rendezvous.widgets.core_widget import CoreWidget


class ProjectInfoPage(Container, CoreWidget):
    def __init__(self, owner_screen: BaseScreen, *children: Widget, **kwargs):
        Container.__init__(self, *children, **kwargs)
        CoreWidget.__init__(self, owner_screen)
        self.border_title = tr("project_info.border")

    def on_mount(self) -> None:
        self.core_mgr.register_hook(
            "selected_project", self.__class__.__name__, self._selected_project_hook
        )
        self._refresh_project_description()
        self._refresh_ssh_instruction()

    def on_unmount(self) -> None:
        self.core_mgr.unregister_hook("selected_project", self.__class__.__name__)

    def _selected_project_hook(self, _project) -> None:
        self._refresh_project_description()
        self._refresh_ssh_instruction()

    def _refresh_ssh_instruction(self) -> None:
        if not self.is_mounted:
            return
        try:
            md = self.query_one("#project-ssh-instruction-md", Markdown)
        except Exception:
            return
        md.update(self.generate_ssh_help())

    def _refresh_project_description(self) -> None:
        if not self.is_mounted:
            return
        try:
            md = self.query_one("#project-description-md", Markdown)
        except Exception:
            return
        md.update(self._project_description_markdown())

    def _project_description_markdown(self) -> str:
        prj = self.core_mgr.selected_project
        if not prj:
            return tr("project_info.select_project_prompt")
        body = (prj.description or "").strip()
        if not body:
            return tr("project_info.no_description", name=prj.name)
        return body

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane(tr("project_info.tab_manage")):
                with VerticalScroll():
                    yield Markdown(
                        self.generate_ssh_help(),
                        id="project-ssh-instruction-md",
                    )
                yield Rule(line_style="ascii")
                yield Button(
                    tr("project_info.start_stop_instance"),
                    id="projectinfo-toggle-instance-btn",
                )
            with TabPane(tr("project_info.tab_info")):
                with VerticalScroll():
                    yield Markdown(
                        self._project_description_markdown(),
                        id="project-description-md",
                    )
            with TabPane(tr("project_info.tab_leaderboard")):
                with VerticalScroll():
                    yield self.generate_leaderboard()

    def generate_leaderboard(self) -> DataTable:
        """Generate the leaderboard tab content"""
        table = DataTable()
        # header and the order
        columns = (
            tr("project_info.leaderboard_col_pos"),
            tr("project_info.leaderboard_col_username"),
            tr("project_info.leaderboard_col_secrets"),
            tr("project_info.leaderboard_col_last_submit"),
            tr("project_info.leaderboard_col_score"),
        )
        header_order = (
            "position",
            "username",
            "found_secrets",
            "last_submit_time",
            "percentage_score",
        )
        # generate each row, highlight a username of the active user
        rows = [
            [
                (
                    Text(l_item[key], style="bold yellow")
                    if key == "username" and l_item[key] == self.active_user.username
                    else l_item[key]
                )
                for key in header_order
            ]
            for l_item in self.core_mgr.get_leaderboard()
        ]
        table.add_columns(*columns)
        table.add_rows(rows)
        return table

    def generate_ssh_help(self) -> str:
        env = Environment(loader=jinja_resources_loader())
        template = env.get_template("run_cluster_instruction.md.j2")
        try:
            container_port, forwarded_port = self._get_ssh_ports()
        except FitRendezvousException as e:
            self.core_mgr.ctf_base.logger.error(str(e))
            return tr("project_info.ssh_error_supervisor")
        return template.render(
            container_port=container_port,
            forwarded_port=forwarded_port,
        )

    def _get_ssh_ports(self) -> tuple[int, int]:
        """`container_port` is published on the host in compose

        Use `forwarded_port` for SSH from outside.
        """
        if not self.active_user or not self.core_mgr.selected_project:
            raise InconsistentState("Missing active user or project is not selected.")
        enrollment = self.core_mgr.ctf_base.enroll_mgr.get_enrollment(
            self.active_user, self.core_mgr.selected_project
        )
        if not enrollment:
            raise InconsistentState(
                f"User {self.active_user.username} is not enrolled "
                f"in {self.core_mgr.selected_project.name}."
            )
        return enrollment.container_port, enrollment.forwarded_port

    @on(Button.Pressed, "#projectinfo-toggle-instance-btn")
    async def toggle_instance(self):
        # TODO: make it more efficient
        if not await self.core_mgr.instance_is_running():
            self.notify(tr("project_info.notify_booting"), severity="warning", timeout=3)
            self.run_worker(
                self.core_mgr.start_user_instance(),
                name="toggle-instance-on",
                exclusive=True,
            )
            btn = self.query_one("#projectinfo-toggle-instance-btn", Button)
            btn.disabled = True
        else:
            self.notify(tr("project_info.notify_shutting_down"), severity="warning", timeout=3)
            self.run_worker(
                self.core_mgr.stop_user_instance(),
                name="toggle-instance-off",
                exclusive=True,
            )
            btn = self.query_one("#projectinfo-toggle-instance-btn", Button)
            btn.disabled = True

    @on(Worker.StateChanged)
    def worker_handler(self, event: Worker.StateChanged):
        worker = event.worker
        if worker.name not in {"toggle-instance-on", "toggle-instance-off"}:
            return

        btn = self.query_one("#projectinfo-toggle-instance-btn", Button)

        if worker.state == WorkerState.ERROR:
            btn.disabled = False
            err = worker.error
            self.notify(
                str(err) if err else tr("project_info.notify_operation_failed"),
                severity="error",
            )
            return

        if worker.state != WorkerState.SUCCESS:
            return

        if worker.name == "toggle-instance-on":
            self.notify(tr("project_info.notify_started"), timeout=3)
            btn.disabled = False
        elif worker.name == "toggle-instance-off":
            self.notify(tr("project_info.notify_shutdown"), timeout=3)
            btn.disabled = False
