import asyncio

import click

from fit_ctf.cli.utils import (
    format_option,
    module_name_option,
    project_option,
    service_name_option,
    user_option,
)
from fit_ctf.ctf_app import CTFApp
from fit_ctf.exceptions import CTFBaseException
from fit_ctf_components.data_parser.yaml_parser import YamlParser
from fit_ctf_components.data_view import get_view
from fit_ctf_components.exceptions import ConfigurationFileNotEditedException
from fit_ctf_components.utils import color_state, document_editor
from fit_ctf_models.cluster import Service
from fit_ctf_models.utils.exceptions import (
    ServiceNotExistException,
    UserNotEnrolledToProjectException,
)


@click.group(name="user-cluster")
@user_option
@project_option
@click.pass_context
def user_cluster(ctx: click.Context, username: str, project_name: str):
    """Manage services of an enrolled user."""
    ctx.obj = ctx.parent.obj  # pyright: ignore
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    try:
        user, project = ctf_app.ue_mgr._get_user_and_project(username, project_name)
        _ = ctf_app.ue_mgr.get_user_enrollment(user, project)
    except CTFBaseException as e:
        click.echo(e)
        exit(1)

    ctx.obj["user"] = user
    ctx.obj["project"] = project


@user_cluster.command(name="start")
@click.pass_context
def start_cluster(ctx: click.Context):
    """Start user instance."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    user = ctx.parent.obj["user"]  # pyright: ignore
    project = ctx.parent.obj["project"]  # pyright: ignore
    asyncio.run(ctf_app.ue_mgr.start_user_cluster(user, project))


@user_cluster.command(name="stop")
@click.pass_context
def stop_cluster(ctx: click.Context):
    """Stop user instance."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    user = ctx.parent.obj["user"]  # pyright: ignore
    project = ctx.parent.obj["project"]  # pyright: ignore
    asyncio.run(ctf_app.ue_mgr.stop_user_cluster(user, project))


@user_cluster.command(name="health-check")
@format_option
@click.pass_context
def health_check(ctx: click.Context, format: str):
    """Display the health check of all the services of the user cluster.

    When tabulate format is used then the states are all colored.
    """
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    user = ctx.parent.obj["user"]  # pyright: ignore
    project = ctx.parent.obj["project"]  # pyright: ignore
    cluster_data = asyncio.run(ctf_app.ue_mgr.user_cluster_health_check(user, project))

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


@user_cluster.command(name="restart")
@click.pass_context
def restart_cluster(ctx: click.Context):
    """Restart user instance."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    user = ctx.parent.obj["user"]  # pyright: ignore
    project = ctx.parent.obj["project"]  # pyright: ignore
    asyncio.run(ctf_app.ue_mgr.restart_user_cluster(user, project))


@user_cluster.command(name="is-running")
@click.pass_context
def user_cluster_is_running(ctx: click.Context):
    """Check if user instance is running."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    user = ctx.parent.obj["user"]  # pyright: ignore
    project = ctx.parent.obj["project"]  # pyright: ignore
    click.echo(asyncio.run(ctf_app.ue_mgr.user_cluster_is_running(user, project)))


@user_cluster.command(name="compile")
@click.pass_context
def compile_compose_file(ctx: click.Context):
    """Compiles user's `compose.yaml` file.

    This step is usually done after editing its list of modules."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    user = ctf_app.user_mgr.get_user(ctx.parent.obj["user"])  # pyright: ignore
    project = ctf_app.prj_mgr.get_project(ctx.parent.obj["project"])  # pyright: ignore
    ctf_app.ue_mgr.compile_compose_file(user, project)


@user_cluster.command(name="build")
@click.pass_context
def build_images(ctx: click.Context):
    """Update images from user's `compose.yaml` file.

    This step is usually done after compiling the YAML file."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    user = ctx.parent.obj["user"]  # pyright: ignore
    project = ctx.parent.obj["project"]  # pyright: ignore
    asyncio.run(ctf_app.ue_mgr.build_user_cluster_images(user, project))


@user_cluster.group(name="services")
@click.pass_context
def services(ctx: click.Context):
    """Manages services of the particular enrollment service."""
    ctx.obj = ctx.parent.obj  # pyright: ignore
    ctf_app: CTFApp = ctx.obj["ctf_app"]
    try:
        ctx.obj["user_enroll"] = ctf_app.ue_mgr.get_user_enrollment(
            ctx.obj["user"], ctx.obj["project"]
        )
    except UserNotEnrolledToProjectException as e:
        click.echo(e)
        exit(1)


@services.command(name="register")
@service_name_option
@module_name_option
@click.option(
    "-L",
    "--is-not-local",
    is_flag=True,
    type=bool,
    help="Set this flag if the module-name refer to a image that will be pulled from the"
    " internet (such as docker.io or similar).",
)
@click.pass_context
def register_service(
    ctx: click.Context, service_name: str, module_name: str, is_not_local: bool
):
    """Register a new instance to the user enrollment."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    user_enroll = ctx.parent.obj["user_enroll"]  # pyright: ignore
    user = ctx.parent.obj["user"]  # pyright: ignore
    project = ctx.parent.obj["project"]  # pyright: ignore
    try:
        service = ctf_app.ue_mgr.get_service(user_enroll, service_name)
        if service:
            click.echo(f"Service {service.service_name} already exists.")
            exit(0)
    except ServiceNotExistException:
        pass

    try:
        doc = document_editor(
            ctf_app.ue_mgr.create_template_user_service(
                user, project, service_name, module_name, not is_not_local
            ).model_dump(),
            {"service_name"},
            "service_editor",
        )
        ctf_app.ue_mgr.register_service(user_enroll, service_name, Service(**doc))
    except ConfigurationFileNotEditedException:
        click.echo("Aborting action.")


@services.command(name="ls")
@click.pass_context
def list_services(ctx: click.Context):
    """Display a list of services of the user enrollment."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    user_enroll = ctx.parent.obj["user_enroll"]  # pyright: ignore
    try:
        services = ctf_app.ue_mgr.list_services(user_enroll)
    except UserNotEnrolledToProjectException as e:
        click.echo(e)
        exit(1)

    services_raw = {k: v.model_dump() for k, v in services.items()}
    click.echo(YamlParser.dump_data(services_raw))


@services.command(name="update")
@service_name_option
@click.pass_context
def update_service(ctx: click.Context, service_name: str):
    """Update a particular service"""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    user_enroll = ctx.parent.obj["user_enroll"]  # pyright: ignore
    try:
        service = ctf_app.ue_mgr.get_service(user_enroll, service_name)
    except ServiceNotExistException as e:
        click.echo(e)
        exit(1)

    try:
        doc = document_editor(service.model_dump(), {"service_name"}, "service_editor")
        ctf_app.ue_mgr.update_service(user_enroll, service_name, Service(**doc))
    except ConfigurationFileNotEditedException:
        click.echo("Aborting action.")


@services.command(name="rm")
@service_name_option
@click.pass_context
def remove_service(ctx: click.Context, service_name: str):
    """Remove the attached module from the user."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    user_enroll = ctx.parent.obj["user_enroll"]  # pyright: ignore

    service = ctf_app.ue_mgr.remove_service(user_enroll, service_name)
    if not service:
        click.echo("Nothing to remove.")
    else:
        click.echo(f"Removed service {service.service_name}")
        click.echo(YamlParser.dump_data(service.model_dump()))
