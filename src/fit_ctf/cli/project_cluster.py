"""CLI commands for project cluster management."""

import asyncio

import click

from fit_ctf.cli.utils import (
    format_option,
    project_option,
    requires_database,
)
from fit_ctf.ctf_app import CTFApp
from fit_ctf.exceptions import CTFBaseException
from fit_ctf_components.data_view import get_view
from fit_ctf_components.utils import color_state
from fit_ctf_models.utils.exceptions import (
    ProjectClusterNotExistException,
    ProjectNotExistException,
)


@click.group(name="project-cluster")
@project_option
@click.pass_context
@requires_database
def project_cluster(ctx: click.Context, project_name: str):
    """Manage project-level cluster (shared infrastructure)."""
    ctx.obj = ctx.parent.obj  # pyright: ignore
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    try:
        project = ctf_app.prj_mgr.get_project(project_name)
        cluster = ctf_app.project_cluster_mgr.get_cluster(project)
    except CTFBaseException as e:
        click.echo(e)
        ctx.exit(1)
    ctx.obj["project"] = project
    ctx.obj["cluster"] = cluster


@project_cluster.command(name="start")
@click.pass_context
def start_cluster(ctx: click.Context):
    """Start project cluster."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    cluster = ctx.parent.obj["cluster"]  # pyright: ignore

    click.echo(f"Starting project cluster '{cluster.name}'...")
    error_code = asyncio.run(ctf_app.project_cluster_mgr.start_cluster(cluster))

    if error_code == 0:
        click.echo("Project cluster started successfully.")
    else:
        click.echo(f"Error starting cluster (exit code: {error_code})")
        ctx.exit(error_code)


@project_cluster.command(name="stop")
@click.pass_context
def stop_cluster(ctx: click.Context):
    """Stop project cluster."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    cluster = ctx.parent.obj["cluster"]  # pyright: ignore

    click.echo(f"Stopping project cluster '{cluster.name}'...")
    error_code = asyncio.run(ctf_app.project_cluster_mgr.stop_cluster(cluster))

    if error_code == 0:
        click.echo("Project cluster stopped successfully.")
    else:
        click.echo(f"Error stopping cluster (exit code: {error_code})")
        ctx.exit(error_code)


@project_cluster.command(name="restart")
@click.pass_context
def restart_cluster(ctx: click.Context):
    """Restart project cluster."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    cluster = ctx.parent.obj["cluster"]  # pyright: ignore

    click.echo(f"Restarting project cluster '{cluster.name}'...")
    error_code = asyncio.run(ctf_app.project_cluster_mgr.restart_cluster(cluster))

    if error_code == 0:
        click.echo("Project cluster restarted successfully.")
    else:
        click.echo(f"Error restarting cluster (exit code: {error_code})")
        ctx.exit(error_code)


@project_cluster.command(name="status")
@click.pass_context
def cluster_status(ctx: click.Context):
    """Check if project cluster is running."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    cluster = ctx.parent.obj["cluster"]  # pyright: ignore

    is_running = asyncio.run(ctf_app.project_cluster_mgr.cluster_is_running(cluster))
    status = "RUNNING" if is_running else "STOPPED"
    click.echo(f"Project cluster '{cluster.name}': {status}")


@project_cluster.command(name="health")
@format_option
@click.pass_context
def health_check(ctx: click.Context, format: str):
    """Display health check of all services in project cluster."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    cluster = ctx.parent.obj["cluster"]  # pyright: ignore

    cluster_data = asyncio.run(ctf_app.project_cluster_mgr.cluster_health_check(cluster))

    if not cluster_data:
        click.echo("No services running in project cluster")
        return

    header = ["Name", "Image", "State"]
    values = [
        [
            i["name"],
            i["image"],
            color_state(i["state"]) if format == "tabulate" else i["state"],
        ]
        for i in cluster_data
    ]
    get_view(format).print_data(header, values)


@project_cluster.command(name="build")
@click.option("-v", "--verbose", is_flag=True, help="Show build output")
@click.pass_context
def build_images(ctx: click.Context, verbose: bool):
    """Build/rebuild project cluster images."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    cluster = ctx.parent.obj["cluster"]  # pyright: ignore

    click.echo(f"Building images for project cluster '{cluster.name}'...")
    error_code = asyncio.run(
        ctf_app.project_cluster_mgr.build_cluster_images(cluster)
    )

    if error_code == 0:
        click.echo("Images built successfully.")
    else:
        click.echo(f"Error building images (exit code: {error_code})")
        ctx.exit(error_code)


@project_cluster.command(name="info")
@click.pass_context
def cluster_info(ctx: click.Context):
    """Show detailed project cluster information."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    cluster = ctx.parent.obj["cluster"]  # pyright: ignore
    project = ctx.parent.obj["project"]  # pyright: ignore

    network_map = ctf_app.project_cluster_mgr.get_network_map(cluster)

    click.echo(f"Project Cluster: {cluster.name}")
    click.echo(f"Project: {project.name}")
    click.echo(f"Project ID: {cluster.project_id.id}")
    click.echo(f"\nNetworks:")
    click.echo(f"  SHARED: {network_map['shared']}")
    click.echo(f"  OPERATIONAL: {network_map['operational']}")
    click.echo(f"\nScenarios ({len(cluster.scenario_configs)}):")

    for scenario_name, config in cluster.scenario_configs.items():
        click.echo(f"  - {scenario_name}")
        click.echo(f"    Services: {len(config.service_configs)}")
        if config.dynamic_secrets:
            click.echo(
                f"    Dynamic Secrets: {', '.join(config.dynamic_secrets.keys())}"
            )


@project_cluster.command(name="list-scenarios")
@format_option
@click.pass_context
def list_scenarios(ctx: click.Context, format: str):
    """List all scenarios in project cluster."""
    cluster = ctx.parent.obj["cluster"]  # pyright: ignore

    if not cluster.scenario_configs:
        click.echo("No scenarios in project cluster")
        return

    headers = ["Scenario", "Services", "Dynamic Secrets"]
    values = [
        [
            name,
            len(config.service_configs),
            len(config.dynamic_secrets),
        ]
        for name, config in cluster.scenario_configs.items()
    ]

    get_view(format).print_data(headers, values)
