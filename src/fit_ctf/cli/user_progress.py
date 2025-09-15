import click

from fit_ctf.cli.utils import format_option, project_option, user_option
from fit_ctf.ctf_app import CTFApp
from fit_ctf_components.data_view import get_view
from fit_ctf_models.user_enrollment import UserEnrollment
from fit_ctf_models.utils.exceptions import (
    CTFModelException,
    SecretAlreadySubmittedException,
    SecretNotFoundException,
)


@click.group(name="user-progress")
@user_option
@project_option
@click.pass_context
def user_progress(ctx: click.Context, username: str, project_name: str):
    """A command to display progresses of users"""
    ctx.obj = ctx.parent.obj  # pyright: ignore
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    try:
        ctx.obj["user_enrollment"] = ctf_app.ue_mgr.get_user_enrollment(
            ctf_app.user_mgr.get_user(username),
            ctf_app.prj_mgr.get_project(project_name),
        )
    except CTFModelException as e:
        click.echo(str(e))
        ctx.exit(1)


@user_progress.command(name="add-secret")
@click.option("-n", "--name", required=True, help="Name of the secret.", type=str)
@click.option("-v", "--value", required=True, help="Secret value.", type=str)
@click.pass_context
def add_secret(ctx: click.Context, name: str, value: str):
    """Add a secret to the progress."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    ue: UserEnrollment = ctx.obj["user_enrollment"]
    try:
        ctf_app.ue_mgr.add_secret(ue, name, value)
    except CTFModelException as e:
        click.echo(str(e))
        ctx.exit(1)


@user_progress.command(name="update-secret")
@click.option("-n", "--name", required=True, help="Name of the secret.", type=str)
@click.option("-v", "--value", required=True, help="Secret value.", type=str)
@click.option(
    "-r",
    "--reset-submitted",
    is_flag=True,
    help="Reset stats if updated secret was previously submitted.",
)
@click.pass_context
def update_secret(ctx: click.Context, name: str, value: str, reset_submitted: bool):
    """Update an existing secret from the list."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    ue: UserEnrollment = ctx.obj["user_enrollment"]
    try:
        ctf_app.ue_mgr.update_secret_value(ue, name, value, reset_submitted)
    except CTFModelException as e:
        click.echo(str(e))
        ctx.exit(1)


@user_progress.command(name="delete-secret")
@click.option("-n", "--name", required=True, help="Name of the secret.", type=str)
@click.pass_context
def delete_secret(ctx: click.Context, name: str):
    """Delete secret from the progress."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    ue: UserEnrollment = ctx.obj["user_enrollment"]
    try:
        ctf_app.ue_mgr.delete_secret(ue, name, False)
    except CTFModelException as e:
        click.echo(str(e))
        ctx.exit(1)


@user_progress.command(name="list-secrets")
@format_option
@click.pass_context
def list_secrets(ctx: click.Context, format: str):
    """Print list of all secrets"""
    ue: UserEnrollment = ctx.obj["user_enrollment"]
    header_order = ["name", "submitted"]
    headers = ["Name", "Submitted"]
    values = [
        [item[key] for key in header_order] for item in ue.progress.list_secrets()
    ]
    get_view(format).print_data(headers, values)


@user_progress.command(name="submit-secret")
@click.option("-v", "--value", required=True, help="Secret value", type=str)
@click.pass_context
def submit_secret(ctx: click.Context, value: str):
    """Validate a secret."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    ue: UserEnrollment = ctx.obj["user_enrollment"]
    try:
        ctf_app.ue_mgr.submit_secret(ue, value)
        click.echo("Secret was successfully submitted.")
    except SecretNotFoundException:
        click.echo("Secret is incorrect.")
        ctx.exit(1)
    except SecretAlreadySubmittedException as e:
        click.echo(str(e))
        ctx.exit(1)


@user_progress.command(name="info")
@format_option
@click.pass_context
def progress_info(ctx: click.Context, format: str):
    """Display user progress information."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    ue: UserEnrollment = ctx.obj["user_enrollment"]
    user = ctf_app.user_mgr.get_doc_by_id(ue.user_id.id)
    if not user:
        click.echo("User not found")
        ctx.exit(1)
    data = {
        "user": user.username,
        "found": ue.progress.found_secrets,
        "total": len(ue.progress.secrets.keys()),
        "last_found": ue.progress.last_submit_time,
    }
    header_order = ["user", "found", "total", "last_found"]
    headers = ["User", "Found", "Total", "Last Found"]
    values = [[data[key] for key in header_order]]
    get_view(format).print_data(headers, values)
