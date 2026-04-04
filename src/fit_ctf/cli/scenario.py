"""CLI commands for scenario management."""

import click

from fit_ctf.cli.utils import format_option, requires_database
from fit_ctf.ctf_app import CTFApp
from fit_ctf_components.data_view import get_view
from fit_ctf_components.utils import file_editor
from fit_ctf_models.utils.exceptions import CTFModelException, ScenarioNotExistException


@click.group(name="scenario")
@click.pass_context
@requires_database
def scenario(ctx: click.Context):
    """Manage scenarios (CTF challenge templates)."""
    ctx.obj = ctx.parent.obj  # pyright: ignore


@scenario.command(name="create")
@click.option("-n", "--name", required=True, help="Scenario name")
@click.pass_context
def create_scenario(ctx: click.Context, name: str):
    """Create a new scenario template."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        ctf_app.scenario_mgr.create_scenario(name)
        click.echo(f"Scenario '{name}' created successfully.")
        click.echo(f"Template directory: {ctf_app.paths.scenario_global / name}")
        click.echo(
            f"Edit template: {ctf_app.paths.scenario_global / name / 'scenario_compose.yaml.j2'}"
        )
    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@scenario.command(name="edit")
@click.option("-n", "--name", required=True, help="Scenario name")
@click.option(
    "--skip-recompile",
    is_flag=True,
    help="Skip recompiling clusters after editing",
)
@click.option(
    "-q",
    "--quiet",
    is_flag=True,
    help="Suppress per-cluster recompilation messages",
)
@click.pass_context
def edit_scenario_template(ctx: click.Context, name: str, skip_recompile: bool, quiet: bool):
    """Edit scenario template file."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    scenario_path = ctf_app.paths.scenario_global / name

    try:
        if not scenario_path.exists():
            raise ScenarioNotExistException(f"Scenario '{name}' not found.")

        template_path = scenario_path / "scenario_compose.yaml.j2"
        if not template_path.exists():
            raise ScenarioNotExistException(f"Template file not found: {template_path}")

        file_editor(template_path)
        click.echo(f"Template edited: {template_path}")

        # Auto-recompile clusters using this scenario (unless skipped)
        if not skip_recompile:
            clusters = ctf_app.scenario_mgr.scenario_usage(name)

            if clusters:
                if not quiet:
                    click.echo(f"Recompiling {len(clusters)} clusters...")
                success_count = 0
                for cluster in clusters:
                    try:
                        ctf_app.user_cluster_mgr.compile_scenario(cluster, name)
                        success_count += 1
                        if not quiet:
                            click.echo(f"  Recompiled {cluster.name}")
                    except Exception as e:
                        click.echo(f"Failed to recompile {cluster.name}: {e}")

                if not quiet:
                    click.echo(f"Recompiled {success_count}/{len(clusters)} clusters.")

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@scenario.command(name="view")
@click.option("-n", "--name", required=True, help="Scenario name")
@click.pass_context
def view_scenario_template(ctx: click.Context, name: str):
    """Edit scenario template file."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    scenario_path = ctf_app.paths.scenario_global / name

    try:
        if not scenario_path.exists():
            raise ScenarioNotExistException(f"Scenario '{name}' not found.")

        template_path = scenario_path / "scenario_compose.yaml.j2"
        with open(template_path, "r") as f:
            for line in f:
                click.echo(line.rstrip())

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@scenario.command(name="usage")
@click.option("-n", "--name", required=True, help="Scenario name")
@format_option
@click.pass_context
def scenario_usage(ctx: click.Context, name: str, format: str):
    """Show which clusters use a scenario."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        clusters = ctf_app.scenario_mgr.scenario_usage(name)

        if not clusters:
            click.echo(f"Scenario '{name}' is not used by any clusters.")
            return

        headers = ["Cluster Name", "Enrollment ID", "Active Scenarios"]
        values = [
            [cluster.name, str(cluster.enrollment_id.id), len(cluster.scenario_names)]
            for cluster in clusters
        ]

        get_view(format).print_data(headers, values)
        click.echo(f"\nTotal clusters using '{name}': {len(clusters)}")

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@scenario.command(name="info")
@click.option("-n", "--name", required=True, help="Scenario name")
@click.pass_context
def scenario_info(ctx: click.Context, name: str):
    """Show detailed information about a scenario."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        scenario_path = ctf_app.paths.scenario_global / name

        if not scenario_path.exists():
            raise ScenarioNotExistException(f"Scenario '{name}' not found.")

        click.echo(f"Scenario: {name}")
        click.echo(f"Path: {scenario_path}")
        click.echo(f"\nFiles and directories:")

        # List template file
        template_path = scenario_path / "scenario_compose.yaml.j2"
        if template_path.exists():
            click.echo(f"  ✓ scenario_compose.yaml.j2 (template)")
        else:
            click.echo(f"  ✗ scenario_compose.yaml.j2 (missing!)")

        # Check for volumes directory
        volumes_dir = scenario_path / "volumes"
        if volumes_dir.exists() and volumes_dir.is_dir():
            volume_count = len(list(volumes_dir.iterdir()))
            click.echo(f"  ✓ volumes/ ({volume_count} items)")
        else:
            click.echo(f"  - volumes/ (not present)")

        # Show usage
        clusters = ctf_app.scenario_mgr.scenario_usage(name)
        click.echo(f"\nUsed by {len(clusters)} cluster(s)")

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@scenario.command(name="list")
@format_option
@click.pass_context
def list_scenarios(ctx: click.Context, format: str):
    """List all scenarios."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    scenarios = ctf_app.scenario_mgr.scenario_overview()

    headers = ["Name", "Used in (clusters)"]
    values = [[s_name, len(clusters)] for s_name, clusters in scenarios.items()]

    get_view(format).print_data(headers, values)


@scenario.command(name="delete")
@click.option("-n", "--name", required=True, help="Scenario name")
@click.confirmation_option(prompt="Are you sure you want to delete this scenario?")
@click.pass_context
def delete_scenario(ctx: click.Context, name: str):
    """Delete a scenario."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        ctf_app.scenario_mgr.delete_scenario(name)
        click.echo(f"Scenario '{name}' deleted successfully.")
    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)
