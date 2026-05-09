import os

import pymongo

from fit_ctf.components.types import EnvInfo


class CTFUtils:
    @staticmethod
    def create_mongo_client(env_info: EnvInfo) -> pymongo.MongoClient:
        """Create and initialize a MongoDB client.

        :param env_info: Environment information containing DB connection details
        :return: Initialized MongoDB client
        """
        db_uri = (
            f"mongodb://{env_info['db_username']}:"
            f"{env_info['db_password']}@{env_info['db_host']}:{env_info['db_port']}/"
        )
        if env_info["db_name"]:
            db_uri += f"{env_info['db_name']}"
        # FIX: remove hardcoded parameter
        db_uri += "?authSource=admin"

        client = pymongo.MongoClient(
            db_uri,
            serverSelectionTimeoutMS=int(os.getenv("DB_CONNECTION_TIMEOUT", "30")),
            tz_aware=True,
        )
        return client
