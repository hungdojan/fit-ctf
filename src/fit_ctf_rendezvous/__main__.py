from dotenv import load_dotenv

from fit_ctf_backend.ctf_manager import CTFManager
from fit_ctf_rendezvous.rendezvous_app import RendezvousApp
from fit_ctf_utils.constants import get_db_info, get_paths
from fit_ctf_utils.types import PathDict


def main():
    load_dotenv()

    db_host, db_name = get_db_info()
    paths = PathDict(
        **{
            key: value
            for key, value in zip(["projects", "users", "modules"], get_paths())
        }
    )

    ctf_mgr = CTFManager(db_host, db_name, paths)

    # start frontend
    app = RendezvousApp(ctf_mgr)
    app.run()


if __name__ == "__main__":
    main()
