import asyncio
import click

from fit_ctf_cli.cli.utils import format_option, module_name_option, requires_database
from fit_ctf_cli.ctf_app import CTFApp
from fit_ctf.components.data_view import get_view
from fit_ctf.models.utils.exceptions import (
    ModuleExistsException,
    ModuleInUseException,
    ModuleNotExistsException,
)


@click.group(name="module")
@click.pass_context
@requires_database
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
        ctx.exit(1)

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
        ctx.exit(1)


@module.command(name="referenced")
@click.option(
    "-pn",
    "--project-name",
    type=str,
    help="Project's name. If not set, the tool will do the referencing on all data.",
)
@click.option(
    "--all-images",
    is_flag=True,
    help="Also list each services.*.image value as its own key (not module dir names).",
)
@format_option
@click.pass_context
def referenced(
    ctx: click.Context, format: str, all_images: bool, project_name: str | None
):
    """Get the module usage count.

    For each module used in the given project (or overall) get its usage count
    in all the clusters.
    """
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    module_count = ctf_app.module_mgr.reference_count(
        project_name, all_images=all_images
    )

    header = ["Module name", "Count"]
    values = [[name, count] for name, count in module_count.items()]
    get_view(format).print_data(header, values)


@module.command(name="build")
@module_name_option
@click.option("-v", "--verbose", is_flag=True, help="Show build output")
@click.pass_context
def build(ctx: click.Context, module_name: str, verbose: bool):
    """Build a module's container image."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    try:
        click.echo(f"Building module '{module_name}'...")
        error_code = asyncio.run(
            ctf_app.module_mgr.build_module(module_name, to_stdout=verbose)
        )
        if error_code == 0:
            click.echo(f"Module '{module_name}' built successfully.")
        else:
            click.echo(f"Error building module (exit code: {error_code})")
            ctx.exit(error_code)
    except ModuleNotExistsException as e:
        click.echo(e)
        ctx.exit(1)


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
        ctx.exit(1)
    click.echo(f"Module `{module_name}` successfully removed.")
