import importlib
import pathlib

import click

from fit_ctf.components.constants import get_paths
from fit_ctf.components.types import PathDict


class LazyGroup(click.Group):
    """A Click Group that lazy-loads subcommands for better performance."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define lazy subcommands with their import paths
        self._lazy_subcommands = {
            "project": ("fit_ctf_cli.cli.project", "project"),
            "user": ("fit_ctf_cli.cli.user", "user"),
            "completion": ("fit_ctf_cli.cli.completion", "completion"),
            "enrollment": ("fit_ctf_cli.cli.enrollment", "enrollment"),
            "user-cluster": ("fit_ctf_cli.cli.user_cluster", "user_cluster"),
            "project-cluster": ("fit_ctf_cli.cli.project_cluster", "project_cluster"),
            "module": ("fit_ctf_cli.cli.module", "module"),
            "data-mgmt": ("fit_ctf_cli.cli.data_mgmt", "data_mgmt"),
            "user-progress": ("fit_ctf_cli.cli.user_progress", "user_progress"),
            "scenario": ("fit_ctf_cli.cli.scenario", "scenario"),
            "cluster": ("fit_ctf_cli.cli.user_cluster", "user_cluster"),
        }

    def list_commands(self, ctx: click.Context):
        base = super().list_commands(ctx)
        curr = sorted(self._lazy_subcommands.keys())
        return base + curr

    def get_command(self, ctx: click.Context, cmd_name: str):
        if cmd_name in self._lazy_subcommands:
            return self._lazy_load(cmd_name)
        return super().get_command(ctx, cmd_name)

    def _lazy_load(self, cmd_name: str):
        modname, cmd_obj_name = self._lazy_subcommands[cmd_name]
        mod = importlib.import_module(modname)
        cmd_object = getattr(mod, cmd_obj_name)
        if not isinstance(cmd_object, click.Command):
            raise ValueError(
                f"Lazy loading of {modname}.{cmd_obj_name} failed by returning "
                "a non-command object"
            )
        return cmd_object


@click.command("cli", cls=LazyGroup)
@click.option(
    "-pd",
    "--project-dir",
    type=click.Path(path_type=pathlib.Path),
    help="Directory that contains project folders.",
)
@click.option(
    "-ud",
    "--user-dir",
    type=click.Path(path_type=pathlib.Path),
    help="Directory that contains user folders.",
)
@click.option(
    "-md",
    "--module-dir",
    type=click.Path(path_type=pathlib.Path),
    help="Directory that contains module folders.",
)
@click.option(
    "-sd",
    "--scenario-dir",
    type=click.Path(path_type=pathlib.Path),
    help="Directory that contains scenario folders.",
)
@click.pass_context
def cli(
    ctx: click.Context,
    project_dir: pathlib.Path | None,
    user_dir: pathlib.Path | None,
    module_dir: pathlib.Path | None,
    scenario_dir: pathlib.Path | None,
):
    """A tool for CTF competition management."""

    paths = PathDict(
        **{
            key: value
            for key, value in zip(
                ["projects", "users", "modules", "scenarios"], get_paths()
            )
        }
    )
    if project_dir:  # pragma: no cover
        paths["projects"] = project_dir
    if user_dir:  # pragma: no cover
        paths["users"] = user_dir
    if module_dir:  # pragma: no cover
        paths["modules"] = module_dir
    if scenario_dir:  # pragma: no cover
        paths["scenarios"] = scenario_dir

    # Store paths in context object for lazy initialization
    # Database connection will be initialized only when needed via @requires_database decorator
    ctx.obj = {"paths": paths}
