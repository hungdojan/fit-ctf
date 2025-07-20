import click

from fit_ctf.cli.utils import project_option


@click.group(name="user_progress")
@click.pass_context
def user_progress(ctx: click.Context):
    """A command to display progresses of users"""
    ctx.obj = ctx.parent.obj  # pyright: ignore


@user_progress.command(name="leaderboard")
@project_option
@click.option(
    "-n",
    help="Display number of NUM users. Set -1 to print the whole leaderboard.",
    type=int,
    default=-1,
)
@click.pass_context
def leaderboard(ctx: click.Context, project_name: str):
    """Display the leaderboard of top NUM users."""
    pass


def sync_project_progresses(ctx: click.Context, project_name: str):
    """Synchronize misaligned progress data."""
    pass
