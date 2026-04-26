import asyncio
import pathlib

import click

from fit_ctf_cli.cli.utils import format_option, requires_database, user_option
from fit_ctf_cli.ctf_app import CTFApp
from fit_ctf.exceptions import CTFBaseException
from fit_ctf.components.auth.auth_interface import AuthInterface
from fit_ctf.components.constants import DEFAULT_PASSWORD_LENGTH
from fit_ctf.components.data_parser.yaml_parser import YamlParser
from fit_ctf.components.data_view import get_view
from fit_ctf.components.types import UserInfoDict
from fit_ctf.models.core.user import UserManager
from fit_ctf.models.utils.exceptions import PublicKeyUploadFail, UserExistsException

#######################
## User CLI commands ##
#######################


@click.group(name="user")
@click.pass_context
@requires_database
def user(ctx: click.Context):
    """A command for user management."""
    ctx.obj = ctx.parent.obj  # pyright: ignore


@user.command(name="create")
@click.option("-u", "--username", required=True, help="Account username.")
@click.option("-p", "--password", default="", help="Account password.")
@click.option("--generate-password", is_flag=True, help="Computer generate a password.")
@click.option("-e", "--email", help="Account email.", default="")
@format_option
@click.pass_context
def create_user(
    ctx: click.Context,
    username: str,
    password: str,
    generate_password: bool,
    email: str,
    format: str,
):
    """Create a new user."""
    user_mgr: UserManager = ctx.parent.obj["ctf_app"].user_mgr  # pyright: ignore
    if password:
        if not AuthInterface.validate_password_strength(password):
            click.echo("Password is not strong enough!")
            ctx.exit(1)
    elif generate_password:
        password = AuthInterface.generate_password(DEFAULT_PASSWORD_LENGTH)
    else:
        click.echo("Missing either `-p` or `--generate-password` option.")
        ctx.exit(1)

    try:
        _, data = user_mgr.create_new_user(username, password, email=email)
    except UserExistsException as e:
        click.echo(e)
        ctx.exit(1)

    # print password
    headers = ["Username", "Password"]
    values = [[data["username"], data["password"]]]
    get_view(format).print_data(headers, values)


@user.command(name="create-multiple")
@click.option(
    "-i",
    "--input_file",
    required=True,
    help="Filepath to a file with new usernames.",
    type=click.Path(path_type=pathlib.Path),
)
@click.option(
    "-dp",
    "--default-password",
    help="Set default passwords to all new users.",
)
@format_option
@click.pass_context
def multiple_create(
    ctx: click.Context,
    input_file: pathlib.Path,
    default_password: str | None,
    format: str,
):
    """Create multiple new users."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    try:
        usernames = []
        with open(input_file, "r") as f:
            usernames = [line.strip() for line in f]

        users = ctf_app.user_mgr.create_multiple_users(usernames, default_password)
        headers = ["Username", "Password"]
        values = [[user[key] for key in ["username", "password"]] for user in users]
        get_view(format).print_data(headers, values)
    except FileNotFoundError:
        click.echo(f"File `{str(input_file.resolve())}` does not exist.")
        ctx.exit(1)
    except PermissionError:
        click.echo(f"Permission denied to access: {str(input_file.resolve())}")
        ctx.exit(1)


@user.command(name="ls")
@format_option
@click.option(
    "-a", "--all", "_all", is_flag=True, help="Display all users (even inactive)."
)
@click.pass_context
def list_users(ctx: click.Context, format: str, _all: bool):
    """Get a list of registered users in the database."""

    def transform_value(key: str, user: UserInfoDict) -> str:
        if key != "projects":
            return user[key]
        elif format == "csv":
            return ",".join(user[key])
        return "\n".join(user[key])

    user_mgr: UserManager = ctx.parent.obj["ctf_app"].user_mgr  # pyright: ignore
    users = user_mgr.get_users_info(None if _all else True)

    values = [
        [
            transform_value(key, user)
            for key in ["username", "active", "role", "email", "projects"]
        ]
        for user in users
    ]
    header = ["Username", "Active", "Role", "Email", "Projects"]
    get_view(format).print_data(header, values)


@user.command(name="get")
@user_option
@click.pass_context
def get_user_info(ctx: click.Context, username: str):
    """Get user information."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    try:
        user_info = ctf_app.user_mgr.get_user_raw(username)
    except CTFBaseException as e:
        click.echo(e)
        ctx.exit(1)
    click.echo(YamlParser.dump_data(user_info))


@user.command(name="enrolled-projects")
@user_option
@format_option
@click.option(
    "-a",
    "--all",
    is_flag=True,
    default=False,
    help="Display inactive projects as well.",
)
@click.pass_context
def enrolled_projects(ctx: click.Context, username: str, format: str, all: bool):
    """Get a list of projects that a user is enrolled to."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    enroll_mgr = ctf_app.enroll_mgr
    try:
        lof_prj = enroll_mgr.get_enrolled_projects_raw(username, all)
    except CTFBaseException as e:
        click.echo(e)
        ctx.exit(1)

    if not lof_prj:
        click.echo("User has is not enrolled to any project.")
        return

    header_order = ["name", "active", "active_users", "max_nof_users"]
    header = [" ".join([i.capitalize() for i in i.split("_")]) for i in header_order]
    values = [[i[key] for key in header_order] for i in lof_prj]
    get_view(format).print_data(header, values)


@user.command(name="change-password")
@user_option
@click.option("-p", "--password", required=True, help="New password.")
@click.pass_context
def change_password(ctx: click.Context, username: str, password: str):
    """Update user's password."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    # TODO: no strength validation
    try:
        ctf_app.user_mgr.change_password(username, password)
    except CTFBaseException as e:
        click.echo(e)
        ctx.exit(1)


@user.command(name="delete")
@click.argument("usernames", nargs=-1)
@click.pass_context
def delete_user(ctx: click.Context, usernames: list[str]):
    """Remove user from the database."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    asyncio.run(ctf_app.user_mgr.delete_users(usernames, ctf_app.enroll_mgr))


@user.command(name="upload-key")
@user_option
@click.option(
    "-f",
    "--file",
    required=True,
    help="Path to the public key.",
    type=click.Path(path_type=pathlib.Path),
)
@click.pass_context
def upload_public_key(ctx: click.Context, username: str, file: pathlib.Path):
    """Upload a user's public key for easier SSH access."""
    with open(file, "rb") as f:
        content = f.read()
    user_mgr: UserManager = ctx.parent.obj["ctf_app"].user_mgr  # pyright: ignore
    try:
        user_mgr.upload_public_key(username, content)
    except PublicKeyUploadFail as e:
        click.echo(str(e))
        ctx.exit(1)
