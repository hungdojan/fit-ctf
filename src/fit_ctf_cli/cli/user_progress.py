import click

from fit_ctf.components.data_view import get_view
from fit_ctf.ctf_app import CTFApp
from fit_ctf.models.core.enrollment import Enrollment
from fit_ctf.models.utils.exceptions import (
    CTFModelException,
    SecretAlreadySubmittedException,
    SecretNotFoundException,
)
from fit_ctf_cli.cli.utils import (
    format_option,
    project_option,
    requires_database,
    user_option,
)


@click.group(name="user-progress")
@user_option
@project_option
@click.pass_context
@requires_database
def user_progress(ctx: click.Context, username: str, project_name: str):
    """A command to display progresses of users"""
    ctx.obj = ctx.parent.obj  # pyright: ignore
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    try:
        ctx.obj["enrollment"] = ctf_app.enroll_mgr.get_enrollment(
            ctf_app.user_mgr.get_user(username),
            ctf_app.prj_mgr.get_project(project_name),
        )
    except CTFModelException as e:
        click.echo(str(e))
        ctx.exit(1)


@user_progress.command(name="list-secrets")
@click.option(
    "-s",
    "--show-secret",
    is_flag=True,
    help="Include expected secret values from cluster config (sensitive).",
)
@format_option
@click.pass_context
def list_secrets(ctx: click.Context, format: str, show_secret: bool):
    """Print list of all secrets (slots from user + project clusters)."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    enrollment: Enrollment = ctx.obj["enrollment"]
    header_order = ["name", "submitted"] + (["flag"] if show_secret else [])
    headers = ["Name", "Submitted"] + (["Secret"] if show_secret else [])
    rows = ctf_app.enroll_mgr.list_secrets_for_display(
        enrollment, ctf_app.prj_mgr, show_flag=show_secret
    )
    values = [[item[key] for key in header_order] for item in rows]
    get_view(format).print_data(headers, values)


@user_progress.command(name="submit-secret")
@click.option("-v", "--value", required=True, help="Secret value", type=str)
@click.pass_context
def submit_secret(ctx: click.Context, value: str):
    """Validate a secret."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    enrollment: Enrollment = ctx.obj["enrollment"]
    try:
        ctf_app.enroll_mgr.submit_secret(enrollment, value, ctf_app.prj_mgr)
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
    enrollment: Enrollment = ctx.obj["enrollment"]
    user = ctf_app.user_mgr.get_doc_by_id(enrollment.user_id.id)
    if not user:
        click.echo("User not found")
        ctx.exit(1)
    total = ctf_app.enroll_mgr.count_submittable_slots(enrollment, ctf_app.prj_mgr)
    data = {
        "user": user.username,
        "found": enrollment.progress.found_secrets,
        "total": total,
        "last_found": enrollment.progress.last_submit_time,
    }
    header_order = ["user", "found", "total", "last_found"]
    headers = ["User", "Found", "Total", "Last Found"]
    values = [[data[key] for key in header_order]]
    get_view(format).print_data(headers, values)
