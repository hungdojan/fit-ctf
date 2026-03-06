import functools
import pathlib

import click
import pymongo.errors

from fit_ctf.ctf_app import CTFApp
from fit_ctf_components.constants import get_env_info

project_option = click.option(
    "-pn", "--project-name", required=True, type=str, help="Project's name."
)

user_option = click.option(
    "-u", "--username", required=True, type=str, help="Account username."
)

service_name_option = click.option(
    "-sn", "--service-name", required=True, help="Service's name."
)

module_name_option = click.option(
    "-mn", "--module-name", required=True, type=str, help="Module's name."
)

format_option = click.option(
    "-f",
    "--format",
    type=click.Choice(["csv", "tabulate"]),
    default="tabulate",
    help="The output format.",
)


def yaml_suffix_validation(
    ctx: click.Context, param: click.Parameter, value: pathlib.Path
):
    if value.suffix not in {".yaml", ".yml"}:
        click.echo(
            "Unsupported file type! The file must have `.yaml` or `.yml` extension."
        )
        exit(1)
    return value


def requires_database(f):
    """Decorator that ensures CTFApp is initialized before running the command.

    This allows database initialization to be lazy - only commands that actually
    need the database will initialize it, improving performance for other commands.
    """

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context()

        # If ctf_app is already initialized, just run the command
        if ctx.obj and "ctf_app" in ctx.obj:
            return f(*args, **kwargs)

        # Initialize CTFApp
        paths = ctx.obj.get("paths", {}) if ctx.obj else {}  # type: ignore
        env_info = get_env_info()

        try:
            ctf_app = CTFApp(env_info, paths)  # type: ignore
            if ctx.obj is None:
                ctx.obj = {}
            ctx.obj["ctf_app"] = ctf_app
        except pymongo.errors.ServerSelectionTimeoutError:
            click.echo(
                "Could not connect to the database. Make sure that the mongo database is running.\n"
                "Use the given script `./manage_db.sh` to manage the database.\n"
                "\n"
                "./manage_db.sh start - start the database.\n"
                "./manage_db.sh stop  - stop the database.\n"
                "./manage_db.sh       - print help"
            )
            raise click.Abort()

        return f(*args, **kwargs)

    return wrapper
