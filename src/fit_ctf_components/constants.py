import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from fit_ctf_components.types import EnvInfo

DEFAULT_PASSWORD_LENGTH = 10
DEFAULT_STARTING_PORT = 10000

# generate root directory paths
load_dotenv()


def get_env_info() -> EnvInfo:
    # TODO: load from shared config
    # TODO: move config to SHARE DIR location
    db_username = os.getenv("DB_USERNAME")
    if not db_username:
        sys.exit("Environment variable `DB_USERNAME` is not set.")

    db_password = os.getenv("DB_PASSWORD")
    if not db_password:
        sys.exit("Environment variable `DB_PASSWORD` is not set.")

    db_host = os.getenv("DB_HOST")
    if not db_host:
        sys.exit("Environment variable `DB_HOST` is not set.")

    db_name = os.getenv("DB_NAME", "")
    db_port = os.getenv("DB_PORT")
    if not db_port:
        sys.exit("Environment variable `DB_PORT` is not set.")

    return {
        "db_username": db_username,
        "db_password": db_password,
        "db_host": db_host,
        "db_name": db_name,
        "db_port": db_port,
    }


def get_paths() -> tuple[Path, Path, Path, Path]:
    default_config_path = f"{os.getenv('HOME', '')}/.local/share/FIT_CTF"
    prj_env = os.getenv("PROJECT_SHARE_DIR", f"{default_config_path}/project")
    user_env = os.getenv("USER_SHARE_DIR", f"{default_config_path}/user")
    module_env = os.getenv("MODULE_SHARE_DIR", f"{default_config_path}/module")
    scenarios_env = os.getenv("SCENARIO_SHARE_DIR", f"{default_config_path}/scenario")

    prj_share_path = Path(os.path.expandvars(prj_env))
    user_share_path = Path(os.path.expandvars(user_env))
    module_share_path = Path(os.path.expandvars(module_env))
    scenario_share_path = Path(os.path.expandvars(scenarios_env))
    return prj_share_path, user_share_path, module_share_path, scenario_share_path
