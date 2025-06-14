import asyncio
import click

from fit_ctf.cli.utils import format_option, module_name_option
from fit_ctf.ctf_app import CTFApp
from fit_ctf_components.data_view import get_view
from fit_ctf_components.exceptions import (
    ModuleExistsException,
    ModuleInUseException,
    ModuleNotExistsException,
)


@click.group(name="module")
@click.pass_context
def module(ctx: click.Context):
    """Manage local modules."""
    ctx.obj = ctx.parent.obj  # pyright: ignore


@module.command(name="create")
@module_name_option
@click.pass_context
def create(ctx: click.Context, module_name: str):
    """Create a new module from the template module."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    try:
        ctf_app.module_mgr.create_module(module_name)
    except ModuleExistsException as e:
        click.echo(e)
        exit(1)

    click.echo(f"Module `{module_name}` successfully created.")


@module.command(name="ls")
@format_option
@click.pass_context
def lists(ctx: click.Context, format: str):
    """List all the local modules located on the host machine."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    modules = ctf_app.module_mgr.list_modules()
    header = ["Name", "Path"]
    values = [[name, str(path.resolve())] for name, path in modules.items()]

    get_view(format).print_data(header, values)


@module.command(name="get-path")
@module_name_option
@click.pass_context
def get(ctx: click.Context, module_name: str):
    """Get a path to the module directory.

    The path can be parsed as an evaluation argument.

    Example:
        cd $(fit-ctf module get -mn <module_name>)
    """
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    try:
        path = ctf_app.module_mgr.get_path(module_name)
        click.echo(str(path.resolve()))
    except ModuleNotExistsException as e:
        click.echo(e)
        exit(1)


@module.command(name="referenced")
@click.option(
    "-pn",
    "--project-name",
    type=str,
    help="Project's name. If not set, the tool will do the referencing on all data.",
)
@format_option
@click.pass_context
def referenced(ctx: click.Context, project_name: str | None, format: str):
    """Get the module usage count.

    For each module used in the given project (or overall) get its usage count
    in all the clusters.
    """
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    module_count = ctf_app.module_mgr.reference_count(project_name)

    header = ["Module name", "Count"]
    values = [[name, count] for name, count in module_count.items()]
    get_view(format).print_data(header, values)


@module.command(name="rm")
@module_name_option
@click.pass_context
def remove(ctx: click.Context, module_name: str):
    """Remove a local module from the machine.

    Only modules that are not referenced anywhere anymore can be removed.
    """
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    try:
        asyncio.run(ctf_app.module_mgr.remove_module(module_name))
    except (ModuleNotExistsException, ModuleInUseException) as e:
        click.echo(e)
        exit(1)
    click.echo(f"Module `{module_name}` successfully removed.")
