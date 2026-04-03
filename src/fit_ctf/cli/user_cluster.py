"""CLI commands for user cluster management."""

import asyncio
import pathlib
from typing import Any

import click

from fit_ctf.cli.utils import (
    format_option,
    project_option,
    requires_database,
    user_option,
)
from fit_ctf.ctf_app import CTFApp
from fit_ctf_components.data_parser.yaml_parser import YamlParser
from fit_ctf_components.data_view import get_view
from fit_ctf_components.exceptions import ConfigurationFileNotEditedException
from fit_ctf_components.utils import yaml_doc_editor
from fit_ctf_models.clusters import ScenarioConfig, ServiceConfig, VolumeConfig
from fit_ctf_models.utils.exceptions import (
    CTFModelException,
)


@click.group(name="user-cluster")
@click.pass_context
@requires_database
def user_cluster(ctx: click.Context):
    """Manage user clusters (user scenario instances)."""
    ctx.obj = ctx.parent.obj  # pyright: ignore


@user_cluster.command(name="add-scenario")
@user_option
@project_option
@click.option("-s", "--scenario", required=True, help="Scenario name to add")
@click.option("-i", "--interactive", is_flag=True, help="Interactively set values")
@click.option(
    "-f",
    "--file",
    type=click.Path(path_type=pathlib.Path),
    help="Service configuration file",
)
@click.pass_context
def add_scenario_to_cluster(
    ctx: click.Context,
    username: str,
    project_name: str,
    scenario: str,
    interactive: bool,
    file: pathlib.Path | None,
):
    """Add a scenario to a user's cluster."""

    def parse_dict_values(raw_dict: dict) -> dict[str, Any]:
        service_configs = {}
        for service, config in raw_dict.items():
            sc = ServiceConfig.Builder()
            for name, value in config.get("env_map", {}).items():
                sc = sc.add_env(name, value)
            for name, value in config.get("port_map", {}).items():
                sc = sc.add_port(name, value)
            for name, value in config.get("volume_map", {}).items():
                sc = sc.add_volume(
                    name,
                    VolumeConfig(
                        src_path=value.get("src_path", ""),
                        template_params=value.get("template_params", {}),
                    ),
                )
            service_configs[service] = sc.build()
        return service_configs

    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)

        service_configs_raw = {}
        if interactive:
            vars = ctf_app.scenario_mgr.fetch_variables(scenario)
            service_configs_raw = yaml_doc_editor(vars)
        elif file:
            service_configs_raw = YamlParser.load_data_file(file)
        else:
            click.echo("`--interactive` or `--file` must be set")
            ctx.exit(1)

        scenario_config = ScenarioConfig.Builder(scenario)
        for name, sc in parse_dict_values(service_configs_raw).items():
            scenario_config.add_service(name, sc)
        scenario_config = scenario_config.build()

        ctf_app.user_cluster_mgr.create_or_update_scenario_config(
            cluster, scenario_config
        )

        click.echo(
            f"Scenario '{scenario}' added to cluster for {username}@{project_name}"
        )
        click.echo(
            "WARNING: Remember to update service configurations with 'cluster edit-service' if needed"
        )
    except ConfigurationFileNotEditedException as e:
        click.echo(e)
        ctx.exit(1)
    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@user_cluster.command(name="remove-scenario")
@user_option
@project_option
@click.option("-s", "--scenario", required=True, help="Scenario name to remove")
@click.pass_context
def remove_scenario_from_cluster(
    ctx: click.Context, username: str, project_name: str, scenario: str
):
    """Remove a scenario from a user's cluster."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)

        ctf_app.user_cluster_mgr.remove_scenario_config(cluster, scenario)

        click.echo(
            f"Scenario '{scenario}' removed from cluster for {username}@{project_name}"
        )
    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@user_cluster.command(name="edit-service")
@user_option
@project_option
@click.option("-s", "--scenario", required=True, help="Scenario name")
@click.option("--service", required=True, help="Service name")
@click.option("-y", "--yes", is_flag=True, help="Confirm changes")
@click.pass_context
def edit_service_config(
    ctx: click.Context,
    username: str,
    project_name: str,
    scenario: str,
    service: str,
    yes: bool,
):
    """Edit service configuration with YAML editor."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)

        if scenario not in cluster.scenario_configs:
            click.echo(f"Error: Scenario '{scenario}' not found in cluster")
            ctx.exit(1)

        scenario_config = cluster.scenario_configs[scenario]

        # Check if service exists
        if service in scenario_config.service_configs:
            # Edit existing service
            click.echo(f"Editing service '{service}' in scenario '{scenario}'...")
            service_data = scenario_config.service_configs[service].model_dump()
        else:
            # Create new service with empty config
            click.echo(f"Creating new service '{service}' in scenario '{scenario}'...")
            service_data = {"env_map": {}, "port_map": {}, "volume_map": {}}

        click.echo("Opening editor...")

        try:
            updated_data = yaml_doc_editor(service_data)
            click.echo("\n✓ Configuration updated")

            # Update service config
            scenario_config.service_configs[service] = ServiceConfig(**updated_data)
            ctf_app.user_cluster_mgr.update_doc(cluster)

            click.echo(
                f"Service '{service}' saved to cluster for {username}@{project_name}"
            )

            # Ask if user wants to compile now
            if yes or click.confirm("\nCompile scenario now?", default=True):
                ctf_app.user_cluster_mgr.compile_scenario(cluster, scenario)
                click.echo(f"Scenario '{scenario}' compiled successfully")

        except ConfigurationFileNotEditedException:
            click.echo("\n✗ No changes made (file not modified)")

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@user_cluster.command(name="add-secret")
@user_option
@project_option
@click.option("-s", "--scenario", required=True, help="Scenario name")
@click.option("-k", "--key", required=True, help="Secret key")
@click.option("-v", "--value", required=True, help="Secret value")
@click.pass_context
def add_dynamic_secret(
    ctx: click.Context,
    username: str,
    project_name: str,
    scenario: str,
    key: str,
    value: str,
):
    """Add a new secret to a scenario."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)

        if scenario not in cluster.scenario_configs:
            click.echo(f"Error: Scenario '{scenario}' not found in cluster")
            ctx.exit(1)

        scenario_config = cluster.scenario_configs[scenario]

        if key in scenario_config.dynamic_secrets:
            click.echo(
                f"Error: Secret '{key}' already exists. Use update-secret to modify."
            )
            ctx.exit(1)

        scenario_config.dynamic_secrets[key] = value
        ctf_app.user_cluster_mgr.update_doc(cluster)
        click.echo(f"Secret '{key}' added to scenario '{scenario}'")

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@user_cluster.command(name="update-secret")
@user_option
@project_option
@click.option("-s", "--scenario", required=True, help="Scenario name")
@click.option("-k", "--key", required=True, help="Secret key")
@click.option("-v", "--value", required=True, help="Secret value")
@click.pass_context
def update_dynamic_secret(
    ctx: click.Context,
    username: str,
    project_name: str,
    scenario: str,
    key: str,
    value: str,
):
    """Update an existing secret in a scenario."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)

        if scenario not in cluster.scenario_configs:
            click.echo(f"Error: Scenario '{scenario}' not found in cluster")
            ctx.exit(1)

        scenario_config = cluster.scenario_configs[scenario]

        if key not in scenario_config.dynamic_secrets:
            click.echo(f"Error: Secret '{key}' not found in scenario '{scenario}'")
            ctx.exit(1)

        scenario_config.dynamic_secrets[key] = value
        ctf_app.user_cluster_mgr.update_doc(cluster)
        click.echo(f"Secret '{key}' updated in scenario '{scenario}'")

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@user_cluster.command(name="remove-secret")
@user_option
@project_option
@click.option("-s", "--scenario", required=True, help="Scenario name")
@click.option("-k", "--key", required=True, help="Secret key to remove")
@click.option("-y", "--yes", is_flag=True, help="Confirm removal")
@click.pass_context
def remove_dynamic_secret(
    ctx: click.Context,
    username: str,
    project_name: str,
    scenario: str,
    key: str,
    yes: bool,
):
    """Remove a secret from a scenario."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)

        if scenario not in cluster.scenario_configs:
            click.echo(f"Error: Scenario '{scenario}' not found in cluster")
            ctx.exit(1)

        scenario_config = cluster.scenario_configs[scenario]

        if key not in scenario_config.dynamic_secrets:
            click.echo(f"Error: Secret '{key}' not found in scenario '{scenario}'")
            ctx.exit(1)

        if not yes and not click.confirm(f"Remove secret '{key}'?", default=False):
            click.echo("Cancelled")
            return

        del scenario_config.dynamic_secrets[key]
        ctf_app.user_cluster_mgr.update_doc(cluster)
        click.echo(f"Secret '{key}' removed from scenario '{scenario}'")

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@user_cluster.command(name="list-secrets")
@user_option
@project_option
@click.option("-s", "--scenario", required=True, help="Scenario name")
@format_option
@click.pass_context
def list_dynamic_secrets(
    ctx: click.Context,
    username: str,
    project_name: str,
    scenario: str,
    format: str,
):
    """List all secrets in a scenario."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)

        if scenario not in cluster.scenario_configs:
            click.echo(f"Error: Scenario '{scenario}' not found in cluster")
            ctx.exit(1)

        scenario_config = cluster.scenario_configs[scenario]

        if not scenario_config.dynamic_secrets:
            click.echo(f"No secrets in scenario '{scenario}'")
            return

        headers = ["Key"]
        values = [[key] for key in scenario_config.dynamic_secrets.keys()]

        get_view(format).print_data(headers, values)

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@user_cluster.command(name="list-scenarios")
@user_option
@project_option
@format_option
@click.pass_context
def list_cluster_scenarios(
    ctx: click.Context, username: str, project_name: str, format: str
):
    """List all scenarios in a user's cluster."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)

        if not cluster.scenario_configs:
            click.echo(f"No scenarios in cluster for {username}@{project_name}")
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
    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@user_cluster.command(name="info")
@user_option
@project_option
@click.pass_context
def cluster_info(ctx: click.Context, username: str, project_name: str):
    """Show detailed cluster information."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)
        network_map = ctf_app.user_cluster_mgr.get_network_map(cluster)

        click.echo(f"Cluster: {cluster.name}")
        click.echo(f"Enrollment ID: {cluster.enrollment_id.id}")
        click.echo(f"\nNetworks:")
        click.echo(f"  SHARED: {network_map['shared']}")
        click.echo(f"  PRIVATE: {network_map['private']}")
        click.echo(f"\nScenarios ({len(cluster.scenario_configs)}):")

        for scenario_name, config in cluster.scenario_configs.items():
            click.echo(f"  - {scenario_name}")
            click.echo(f"    Services: {len(config.service_configs)}")
            if config.dynamic_secrets:
                click.echo(
                    f"    Dynamic Secrets: {', '.join(config.dynamic_secrets.keys())}"
                )
            for service_name, service_config in config.service_configs.items():
                click.echo(f"      • {service_name}")
                if service_config.env_map:
                    click.echo(f"        Env vars: {len(service_config.env_map)}")
                if service_config.port_map:
                    click.echo(f"        Ports: {len(service_config.port_map)}")
                if service_config.volume_map:
                    click.echo(f"        Volumes: {len(service_config.volume_map)}")

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@user_cluster.command(name="compile")
@user_option
@project_option
@click.option("-s", "--scenario", help="Scenario name (compile all if not specified)")
@click.pass_context
def compile_cluster(
    ctx: click.Context, username: str, project_name: str, scenario: str | None
):
    """Compile scenario templates for a cluster."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)

        if scenario:
            # Compile specific scenario
            if scenario not in cluster.scenario_configs:
                click.echo(f"Error: Scenario '{scenario}' not found in cluster")
                ctx.exit(1)
            ctf_app.user_cluster_mgr.compile_scenario(cluster, scenario)
            click.echo(f"Scenario '{scenario}' compiled for {username}@{project_name}")
        else:
            # Compile all scenarios
            for scenario_name in cluster.scenario_configs.keys():
                ctf_app.user_cluster_mgr.compile_scenario(cluster, scenario_name)
            click.echo(
                f"All scenarios compiled for {username}@{project_name} ({len(cluster.scenario_configs)} scenarios)"
            )

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@user_cluster.command(name="start")
@user_option
@project_option
@click.option("-v", "--verbose", is_flag=True, help="Show compose engine output")
@click.pass_context
def start_cluster(
    ctx: click.Context, username: str, project_name: str, verbose: bool
):
    """Start all scenarios in a user's cluster."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)

        error_code = asyncio.run(
            ctf_app.user_cluster_mgr.start_cluster(cluster, verbose=verbose)
        )

        if error_code == 0:
            click.echo(f"Cluster started for {username}@{project_name}")
        else:
            click.echo(f"Error starting cluster (exit code: {error_code})")
            ctx.exit(error_code)

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@user_cluster.command(name="stop")
@user_option
@project_option
@click.option("-v", "--verbose", is_flag=True, help="Show compose engine output")
@click.pass_context
def stop_cluster(
    ctx: click.Context, username: str, project_name: str, verbose: bool
):
    """Stop all scenarios in a user's cluster."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)

        error_code = asyncio.run(
            ctf_app.user_cluster_mgr.stop_cluster(cluster, verbose=verbose)
        )

        if error_code == 0:
            click.echo(f"Cluster stopped for {username}@{project_name}")
        else:
            click.echo(f"Error stopping cluster (exit code: {error_code})")
            ctx.exit(error_code)

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@user_cluster.command(name="restart")
@user_option
@project_option
@click.option("-v", "--verbose", is_flag=True, help="Show compose engine output")
@click.pass_context
def restart_cluster(
    ctx: click.Context, username: str, project_name: str, verbose: bool
):
    """Restart all scenarios in a user's cluster."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)

        error_code = asyncio.run(
            ctf_app.user_cluster_mgr.restart_cluster(cluster, verbose=verbose)
        )

        if error_code == 0:
            click.echo(f"Cluster restarted for {username}@{project_name}")
        else:
            click.echo(f"Error restarting cluster (exit code: {error_code})")
            ctx.exit(error_code)

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@user_cluster.command(name="logs")
@user_option
@project_option
@click.option(
    "--tail",
    default=500,
    show_default=True,
    type=int,
    help="Max lines per service",
)
@click.option("-s", "--service", default=None, help="Limit to one compose service")
@click.option(
    "--no-log-stdout",
    is_flag=True,
    help="Write logs only to LOG_DEST files, not the terminal",
)
@click.pass_context
def user_cluster_logs(
    ctx: click.Context,
    username: str,
    project_name: str,
    tail: int,
    service: str | None,
    no_log_stdout: bool,
):
    """Show recent container logs for a user's cluster."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)
        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)

        error_code = asyncio.run(
            ctf_app.user_cluster_mgr.compose_logs(
                cluster,
                tail=tail,
                service=service,
                to_stdout=not no_log_stdout,
            )
        )
        if error_code != 0:
            click.echo(f"Error fetching logs (exit code: {error_code})")
            ctx.exit(error_code)

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@user_cluster.command(name="status")
@user_option
@project_option
@click.pass_context
def cluster_status(ctx: click.Context, username: str, project_name: str):
    """Check if cluster is running."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)

        is_running = asyncio.run(ctf_app.user_cluster_mgr.cluster_is_running(cluster))

        status = "RUNNING" if is_running else "STOPPED"
        click.echo(f"{username}@{project_name}: {status}")

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)


@user_cluster.command(name="health")
@user_option
@project_option
@format_option
@click.pass_context
def cluster_health(ctx: click.Context, username: str, project_name: str, format: str):
    """Check health of all services in cluster."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore

    try:
        user = ctf_app.user_mgr.get_user(username)
        project = ctf_app.prj_mgr.get_project(project_name)
        enrollment = ctf_app.enroll_mgr.get_enrollment(user, project)

        cluster = ctf_app.user_cluster_mgr.get_cluster(enrollment)

        health = asyncio.run(ctf_app.user_cluster_mgr.cluster_health_check(cluster))

        if not health:
            click.echo(f"No services running in cluster for {username}@{project_name}")
            return

        headers = ["Name", "State", "Image"]
        values = [[h["name"], h["state"], h["image"]] for h in health]

        get_view(format).print_data(headers, values)

    except CTFModelException as e:
        click.echo(f"Error: {e}")
        ctx.exit(1)
