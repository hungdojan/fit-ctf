import pathlib

import click

from fit_ctf.components.data_view import get_view
from fit_ctf.ctf_app import CTFApp
from fit_ctf.exceptions import CTFBaseException
from fit_ctf_cli.cli.utils import (
    format_option,
    project_option,
    requires_database,
    yaml_suffix_validation,
)


@click.group(name="data-mgmt")
@click.pass_context
@requires_database
def data_mgmt(ctx: click.Context):
    """Manage data with config files."""
    ctx.obj = ctx.parent.obj  # pyright: ignore


@data_mgmt.command(name="export")
@project_option
@click.option(
    "-o",
    "--output-file",
    default="project_archive.zip",
    help="Final ZIP file name.",
    show_default=True,
)
@click.pass_context
def export_data(ctx: click.Context, project_name: str, output_file: str):
    """Export project data from the host machine.

    Generates a ZIP file containing all the project configuration files, including
    users and modules.
    """
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    try:
        ctf_app.export_project(project_name, output_file)
    except CTFBaseException as e:
        click.echo(e)


@data_mgmt.command(name="import")
@click.option(
    "-i",
    "--input-file",
    required=True,
    type=click.Path(path_type=pathlib.Path, exists=True),
    help="The archive filepath.",
)
@click.pass_context
def import_data(ctx: click.Context, input_file: pathlib.Path):
    """Import project data from external machine.

    Loads the ZIP archive containing important data required for creating similar
    environment as the origin.
    """
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    try:
        ctf_app.import_project(input_file)
    except CTFBaseException as e:
        click.echo(e)


@data_mgmt.command(name="setup")
@click.option(
    "-i",
    "--input-file",
    required=True,
    type=click.Path(path_type=pathlib.Path, exists=True),
    callback=yaml_suffix_validation,
    help="A path to the YAML configuration file.",
)
@click.option("-E", "--exist-ok", is_flag=True, help="Ignore objects that already exist.")
@click.option(
    "-D",
    "--dry-run",
    is_flag=True,
    help="Simulate running the setup without applying any changes.",
)
@format_option
@click.pass_context
def setup_data(
    ctx: click.Context,
    input_file: pathlib.Path,
    exist_ok: bool,
    dry_run: bool,
    format: str,
):
    """Setup environment from the YAML config file.

    The schema of the design is located at `schemas/v1/setup.yaml`
    """
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        new_users = ctf_app.setup_env_from_file(input_file, exist_ok, dry_run)
        if new_users:
            headers = ["Username", "Password"]
            values = [[user[label] for label in ["username", "password"]] for user in new_users]
            get_view(format).print_data(headers, values)
    except CTFBaseException as e:
        click.echo(e)
