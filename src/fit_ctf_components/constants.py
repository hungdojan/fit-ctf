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
    # TODO: move config to SHARE DIR location
    db_host = os.getenv("DB_HOST")
    if not db_host:
        sys.exit("Environment variable `DB_HOST` is not set.")

    db_name = os.getenv("DB_NAME")
    if not db_name:
        sys.exit("Environment variable `DB_NAME` is not set.")

    app_secret = os.getenv("APP_SECRET")
    if not app_secret:
        sys.exit("Environment variable `APP_SECRET` is not set.")
    return {"db_host": db_host, "db_name": db_name, "app_secret": app_secret}


def get_paths() -> tuple[Path, Path, Path]:
    default_config_path = f"{os.getenv('HOME', '')}/.local/share/FIT_CTF"
    prj_env = os.getenv("PROJECT_SHARE_DIR", f"{default_config_path}/project")
    user_env = os.getenv("USER_SHARE_DIR", f"{default_config_path}/user")
    module_env = os.getenv("MODULE_SHARE_DIR", f"{default_config_path}/module")

    prj_share_path = Path(prj_env)
    user_share_path = Path(user_env)
    module_share_path = Path(module_env)
    return prj_share_path, user_share_path, module_share_path
