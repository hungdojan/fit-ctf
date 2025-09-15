import asyncio

import click

from fit_ctf.cli.utils import format_option, project_option
from fit_ctf.ctf_app import CTFApp
from fit_ctf.exceptions import CTFBaseException
from fit_ctf_components.data_parser.yaml_parser import YamlParser
from fit_ctf_components.data_view import get_view
from fit_ctf_components.utils import color_state
from fit_ctf_models.project import ProjectManager

##########################
## Project CLI commands ##
##########################


@click.group(name="project")
@click.pass_context
def project(
    ctx: click.Context,
):
    """A command for project management."""
    ctx.obj = ctx.parent.obj  # pyright: ignore


@project.command(name="create")
@click.option(
    "-pn",
    "--project-name",
    help="Project's name (also serves as project id).",
    required=True,
)
@click.option(
    "-mu",
    "--max-nof-users",
    help="Max number of users.",
    default=1000,
    show_default=True,
    type=int,
)
@click.option(
    "-p",
    "--starting-port-bind",
    help="A starting port value for each user. "
    "Each user will received a port from the range from <starting-port-bind>"
    "to <starting-port-bind + max-nof-users>. "
    "If set to -1, the tool will automatically assign an available port value."
    "User can choose a number between 10_000 to 65_535.",
    default=-1,
    show_default=True,
    type=int,
)
@click.option(
    "-de", "--description", help="A project description.", default="", show_default=True
)
@click.pass_context
def create_project(
    ctx: click.Context,
    project_name: str,
    max_nof_users: int,
    starting_port_bind: int,
    description: str,
):
    """Create and initialize a new project.

    This command generate a basic project from the template and stores
    it in the `dest_dir` directory. Make sure that `dest_dir` exists."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    try:
        prj = ctf_app.prj_mgr.init_project(
            project_name,
            max_nof_users,
            starting_port_bind,
            description,
        )
        click.echo(f"Project `{prj.name}` was successfully generated.")
    except CTFBaseException as e:
        click.echo(e)
        ctx.exit(1)


@project.command(name="ls")
@format_option
@click.option(
    "-a",
    "--all",
    "_all",
    is_flag=True,
    help="Display both active and inactive projects.)",
)
@click.pass_context
def list_projects(ctx: click.Context, format: str, _all: bool):
    """Display existing projects.

    This command by default displays only active projects. Use `-a` flag to
    display inactive projects.

    Displays following states:
        - active state
        - project name
        - max number of users
        - number of active users enrolled to the project
    """
    prj_mgr: ProjectManager = ctx.parent.obj["ctf_app"].prj_mgr  # pyright: ignore
    lof_prj = prj_mgr.get_projects_raw(include_inactive=_all)
    if not lof_prj:
        click.echo("No project found!")
        return
    header_order = ["name", "active", "active_users", "max_nof_users"]
    headers = ["Name", "Active", "Users", "Capacity"]
    values = [[i[key] for key in header_order] for i in lof_prj]
    get_view(format).print_data(headers, values)


@project.command(name="get-info")
@project_option
@click.pass_context
def get_project_info(ctx: click.Context, project_name: str):
    """Display project PROJECT_NAME's information.

    Dumps all information about a selected project.
    """
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    prj = ctf_app.prj_mgr.get_doc_by_filter_raw({"name": project_name}, {"_id": 0})
    if prj:
        click.echo(YamlParser.dump_data(prj))
    else:
        click.echo(f"Project `{project_name}` not found.")


@project.command(name="enrolled-users")
@project_option
@format_option
@click.option(
    "-a",
    "--all",
    is_flag=True,
    default=False,
    help="Display inactive enrollments as well.",
)
@click.pass_context
def enrolled_users(ctx: click.Context, project_name: str, format: str, all: bool):
    """Get list of active users that are enrolled to the PROJECT_NAME.

    Displays following states:
        - active state
        - account username
        - account role
        - path to home mounting directory/volume
        - forwarded port (visible from the outside)
    """
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    try:
        lof_active_users = ctf_app.ue_mgr.get_user_enrollments_for_project_raw(
            project_name, all
        )
    except CTFBaseException as e:
        click.echo(e)
        ctx.exit(1)
    if not lof_active_users:
        click.echo("No active users found.")
        return

    header_order = ["username", "role", "active", "forwarded_port", "mount"]
    header = [" ".join([i.capitalize() for i in i.split("_")]) for i in header_order]
    values = [[i[key] for key in header_order] for i in lof_active_users]
    get_view(format).print_data(header, values)


@project.command(name="generate-firewall-rules")
@click.option("-ip", "--ip-addr", required=True, help="The destination IP address.")
@click.option(
    "-o",
    "--output",
    default="firewall.sh",
    help="Destination file where the script content will be written.",
)
@project_option
@click.pass_context
def firewall_rules(ctx: click.Context, project_name: str, ip_addr: str, output: str):
    """Generate a BASH script with port forwarding rules for PROJECT_NAME.

    The command used in the script are written for `firewalld` application.
    """
    prj_mgr: ProjectManager = ctx.parent.obj["ctf_app"].prj_mgr  # pyright: ignore
    prj_mgr.generate_port_forwarding_script(project_name, ip_addr, output)


@project.command(name="reserved-ports")
@format_option
@click.pass_context
def used_ports(ctx: click.Context, format: str):
    """Returns list of reserved ports.

    Displays a list of projects and their reserved port range."""
    prj_mgr: ProjectManager = ctx.parent.obj["ctf_app"].prj_mgr  # pyright: ignore
    lof_prj = prj_mgr.get_reserved_ports()
    if not lof_prj:
        click.echo("No project found!")
        return
    header = ["ID", "Name", "Min Port", "Max Port"]
    values = [
        [i[key] for key in ["_id", "name", "min_port", "max_port"]] for i in lof_prj
    ]
    get_view(format).print_data(header, values)


@project.command(name="resources")
@project_option
@click.pass_context
def resources_usage(ctx: click.Context, project_name: str):
    """Display the resource usage of a given project."""
    prj_mgr: ProjectManager = ctx.parent.obj["ctf_app"].prj_mgr  # pyright: ignore
    try:
        asyncio.run(prj_mgr.get_resource_usage(project_name))
    except CTFBaseException as e:
        click.echo(e)


@project.command("delete")
@project_option
@click.pass_context
def delete_project(ctx: click.Context, project_name: str):
    """Delete an existing project."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    asyncio.run(ctf_app.prj_mgr.delete_project(project_name))
    click.echo(f"Project `{project_name}` deleted successfully.")


@project.command(name="running-cluster")
@project_option
@format_option
@click.pass_context
def running_clusters_info(ctx: click.Context, project_name: str, format: str):
    """Display all the status of all the active clusters.

    When tabulate format is used, the status column is colored."""
    ctf_app: CTFApp = ctx.parent.obj["ctf_app"]  # pyright: ignore
    services_info = asyncio.run(ctf_app.prj_mgr.get_all_services_info(project_name))
    data_buffer = []
    for info in services_info:
        data_buffer.append(
            {
                "image": info["Image"],
                "name": info["Names"][0],
                "networks": "\n".join(info["Networks"]) if info["Networks"] else "",
                "cluster_type": (
                    info["Labels"]["cluster_type"]
                    if info["Labels"].get("cluster_type")
                    else ""
                ),
                "state": (
                    color_state(info["State"])
                    if format == "tabulate"
                    else info["State"]
                ),
                "ports": (
                    "\n".join([str(p["host_port"]) for p in info["Ports"]])
                    if info["Ports"]
                    else ""
                ),
            }
        )
    header_order = ["name", "image", "cluster_type", "networks", "ports", "state"]
    header = [" ".join([i.capitalize() for i in i.split("_")]) for i in header_order]
    values = [[i[key] for key in header_order] for i in data_buffer]
    get_view(format).print_data(header, values)


@project.command(name="leaderboard")
@project_option
@format_option
@click.option(
    "-n",
    "--nof-users",
    help="Display number of NUM users. Set -1 to print the whole leaderboard.",
    type=int,
    default=-1,
)
@click.pass_context
def leaderboard(ctx: click.Context, project_name: str, format: str, nof_users: int):
    """Display the leaderboard of top NUM users."""
    pass


@project.command("sync-leaderboard-data")
@project_option
def sync_project_progresses(ctx: click.Context, project_name: str):
    """Synchronize misaligned progress data."""
    pass
