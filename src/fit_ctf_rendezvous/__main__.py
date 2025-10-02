import os

from dotenv import load_dotenv

from fit_ctf.ctf_base import CTFBase
from fit_ctf_components.constants import get_env_info, get_paths
from fit_ctf_components.container_client import get_c_client_by_name
from fit_ctf_components.types import PathDict
from fit_ctf_rendezvous.core_manager import CoreManager
from fit_ctf_rendezvous.rendezvous_app import RendezvousApp


def main():
    load_dotenv()

    env_info = get_env_info()
    paths = PathDict(
        **{
            key: value
            for key, value in zip(["projects", "users", "modules"], get_paths())
        }
    )

    ctf_base = CTFBase(
        env_info,
        paths,
        get_c_client_by_name(os.getenv("CONTAINER_CLIENT", "")),
    )
    core_mgr = CoreManager(ctf_base)

    # start frontend
    app = RendezvousApp(core_mgr)
    app.run()


if __name__ == "__main__":
    main()
