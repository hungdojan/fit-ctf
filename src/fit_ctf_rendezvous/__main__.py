import os

from dotenv import load_dotenv

from fit_ctf.components.constants import get_env_info, get_paths
from fit_ctf.components.container_client import get_c_client_by_name
from fit_ctf.components.types import PathDict
from fit_ctf.ctf_app import CTFApp
from fit_ctf.ctf_base import CTFBase
from fit_ctf_rendezvous.rendezvous_app import RendezvousApp


def main():
    load_dotenv()
    # Locale: English on startup; optional FIT_RENDEZVOUS_LANG=en|cs to override.

    env_info = get_env_info()
    paths = PathDict(
        **{
            key: value
            for key, value in zip(["projects", "users", "modules", "scenarios"], get_paths())
        }
    )

    mongo_client = CTFApp.create_mongo_client(env_info)

    ctf_base = CTFBase(
        env_info,
        paths,
        mongo_client,
        get_c_client_by_name(os.getenv("CONTAINER_CLIENT", "")),
    )

    app = RendezvousApp(ctf_base)
    app.run()


if __name__ == "__main__":
    main()
