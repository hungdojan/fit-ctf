import os
import shutil
from pathlib import Path

import jinja2
from dotenv import load_dotenv
from invoke.context import Context
from invoke.tasks import task

load_dotenv()


def root_dirpath() -> Path:
    return Path(os.path.dirname(os.path.realpath(__file__)))


@task
def db_start(ctx: Context):
    print("Starting DB...")
    ctx.run("podman-compose -f ./db/compose.yaml --env-file .env up -d")


@task
def db_stop(ctx: Context):
    print("Stoping DB...")
    ctx.run("podman-compose -f ./db/compose.yaml --env-file .env down")


@task(pre=[db_stop], post=[db_start])
def db_restart(_: Context):
    pass


@task
def db_shell(ctx: Context):
    ctx.run(
        f"""podman exec \\
            -it ctf-database-mongo mongosh \\
            -u {os.getenv('DB_USERNAME')} \\
            -p {os.getenv('DB_PASSWORD')}
        """,
        pty=True,
    )


@task
def db_deploy(
    _: Context,
    db_username: str,
    db_password: str,
    db_name: str,
):
    config_dir = root_dirpath() / "db" / "mongodb-quadlet"
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(config_dir))
    template = env.get_template("mongodb.container.j2")
    container_systemd_dir = Path.home() / ".config" / "containers" / "systemd"
    with open(container_systemd_dir / "mongodb.container", "w") as f:
        f.write(
            template.render(
                db_vals={
                    "username": db_username,
                    "password": db_password,
                    "name": db_name,
                }
            )
        )
    shutil.copy(config_dir / "mongodb.volume", container_systemd_dir / "mongodb.volume")
    pass


@task
def generate_env(
    _: Context,
    db_username: str,
    db_password: str,
    db_name: str,
    db_host: str = "localhost",
):
    config_dir = root_dirpath() / "config" / "setup"
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(config_dir))
    template = env.get_template("env_example")
    with open(root_dirpath() / ".env-test", "w") as f:
        f.write(
            template.render(
                db_vals={
                    "username": db_username,
                    "password": db_password,
                    "name": db_name,
                    "host": db_host,
                }
            )
        )


@task
def setup_sshd(_: Context, user: str, rdz_port: int, fitctf_dirpath: str):
    config_dir = root_dirpath() / "config" / "setup"
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(config_dir))
    template = env.get_template("99-ctf-rule.conf")
    with open(root_dirpath() / "99-ctf-rule.conf", "w") as f:
        f.write(
            template.render(user=user, rdz_port=rdz_port, fitctf_dirpath=fitctf_dirpath)
        )
