import asyncio
import concurrent.futures
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from shutil import copytree
from typing import cast

import pymongo
from dateutil import parser
from jsonschema.exceptions import ValidationError

import fit_ctf_models.project as project
from fit_ctf.ctf_base import CTFBase
from fit_ctf.exceptions import (
    CTFBaseException,
    ImportFileCorruptedException,
)
from fit_ctf_components.auth.auth_interface import AuthInterface
from fit_ctf_components.constants import DEFAULT_PASSWORD_LENGTH
from fit_ctf_components.container_client import get_c_client_by_name
from fit_ctf_components.data_parser.yaml_parser import YamlParser
from fit_ctf_components.types import (
    DatabaseDumpDict,
    EnvInfo,
    NewUserDict,
    PathDict,
    SetupDict,
)
from fit_ctf_models.clusters.config_models import scenario_config_from_dict
from fit_ctf_models.clusters.user_cluster import UserCluster

# Service management deprecated - moved to cluster configurations
from fit_ctf_models.secret import SecretSubmissionLogEntry, SolvedSecretRecord
from fit_ctf_models.user_progress import UserProgress
from fit_ctf_models.utils.exceptions import (
    ProjectExistsException,
    UserExistsException,
)
from fit_ctf_models.utils.mongo_queries import MongoQueries
from fit_ctf_templates import TEMPLATE_PATH_MAP


class CTFApp(CTFBase):
    def __init__(
        self,
        env_info: EnvInfo,
        paths: PathDict,
        mongo_client: pymongo.MongoClient | None = None,
    ):
        """Constructor method

        :param host: A URL to connect to the database.
        :type host: str
        :param db_name: Name of the database that contain CTF data.
        :type db_name: str
        """
        if mongo_client is None:
            mongo_client = self.create_mongo_client(env_info)

        super().__init__(
            env_info,
            paths,
            mongo_client,
            get_c_client_by_name(os.getenv("CONTAINER_CLIENT", "")),
        )
        self._init_paths(paths)

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

    def _init_paths(self, paths: PathDict):
        """Initialize path directories for the current session."""
        self._paths = paths
        for obj_name, path in self._paths.items():
            path = cast(Path, path)
            if not path.exists():
                self.logger.print(
                    f"Creating central {obj_name} directory `{str(path.resolve())}`...",
                    logger_name=f"{__name__}_print",
                )
                path.mkdir(parents=True, exist_ok=True)

        self.init_tool()

    def init_tool(self):
        """Initialize base images."""
        for module_path in TEMPLATE_PATH_MAP["modules"].iterdir():
            if (self.paths.module_global / module_path.name).exists():
                continue
            if module_path.is_dir():
                copytree(module_path, self.paths.module_global / module_path.name)
        for scenario_path in TEMPLATE_PATH_MAP["scenarios"].iterdir():
            if (self.paths.scenario_global / scenario_path.name).exists():
                continue
            if scenario_path.is_dir():
                copytree(scenario_path, self.paths.scenario_global / scenario_path.name)

    def export_all(self, output_zip_name: str):
        raise NotImplementedError()

    def _load_all_data_to_dict(self, project: "project.Project") -> dict:
        data = {}
        # Project document (export shape for database_dump.yaml)
        data["project"] = {k: v for k, v in project.model_dump().items() if k != "_id"}

        # User rows are whoever is enrolled in this project
        users = self.enroll_mgr.get_enrollments_for_project(project, True)
        data["users"] = [
            {k: v for k, v in u.model_dump().items() if k != "_id"} for u in users
        ]
        pipeline = MongoQueries.export_enrollments(project)
        enrollments = list(self.enroll_mgr.collection.aggregate(pipeline))

        # Per enrollment: normalize secrets for YAML, attach optional UserCluster export
        clusters = []

        for enrollment in enrollments:
            enrollment_ref = f"{enrollment['user']}@{enrollment['project']}"

            progress = enrollment["progress"]
            for v in (progress.get("solved_secrets") or {}).values():
                if not isinstance(v, dict):
                    continue
                user_id = v.pop("user_id", None)
                user = None
                if user_id:
                    user = self.user_mgr.get_doc_by_id(user_id)
                v["user"] = user.username if user else None
                if v.get("submitted_at"):
                    v["submitted_at"] = v["submitted_at"].isoformat()
            for entry in progress.get("submission_log") or []:
                if isinstance(entry, dict) and entry.get("timestamp"):
                    entry["timestamp"] = entry["timestamp"].isoformat()
            if progress.get("last_submit_time"):
                progress["last_submit_time"] = progress["last_submit_time"].isoformat()

            cluster = self.user_cluster_mgr.get_doc_by_filter(
                **{"enrollment_id.$id": enrollment["_id"]}
            )
            if cluster:
                cluster_dict = {
                    "name": cluster.name,
                    "scenario_configs": {
                        n: c.model_dump() for n, c in cluster.scenario_configs.items()
                    },
                    "enrollment_ref": enrollment_ref,
                }
                clusters.append(cluster_dict)

            enrollment.pop("_id", None)
            enrollment["enrollment_id"] = enrollment_ref

        data["enrollments"] = enrollments
        data["clusters"] = clusters

        # Project-level cluster (admin / shared scenarios)
        pc = self.project_cluster_mgr.get_doc_by_filter(
            **{"project_id.$id": project.id}
        )
        if pc:
            data["project_cluster"] = {
                "name": pc.name,
                "scenario_names": pc.scenario_names,
                "scenario_configs": {
                    n: c.model_dump() for n, c in pc.scenario_configs.items()
                },
            }
        else:
            data["project_cluster"] = None

        # Module names referenced by this project (for ZIP module tree)
        module_count = self.module_mgr.reference_count(project.name)
        data["modules"] = [k for k, v in module_count.items() if v > 0]
        return data

    def _add_user_files_to_zipfile(self, zf: zipfile.ZipFile, data: dict):
        for username in [u["username"] for u in data["users"]]:
            # get path to shadow file
            user_root_dir = self.paths.user_global / username
            filepath = user_root_dir / "shadow"
            parentpath = os.path.relpath(filepath, user_root_dir)
            arcname = os.path.join(self.paths.user_global.name, username, parentpath)

            # add a shadow file to the archive
            zf.write(filepath, arcname)

            # create an empty home directory
            zf.writestr(
                zipfile.ZipInfo(
                    os.path.join(self.paths.user_global.name, username, "home/")
                ),
                "",
            )

    def _add_module_files_to_zipfile(self, zf: zipfile.ZipFile, data: dict):
        module_root_dir = self.paths.module_global
        for module_name in data["modules"]:
            for dirpath, _, filenames in os.walk(module_root_dir / module_name):
                for filename in filenames:

                    # Write the file named filename to the archive,
                    # giving it the archive name 'arcname'.
                    # filepath = os.path.join(dirpath, filename)
                    filepath = Path(dirpath) / filename
                    parentpath = os.path.relpath(
                        filepath, module_root_dir / module_name
                    )
                    arcname = os.path.join(
                        self.paths.module_global.name,
                        os.path.basename(module_root_dir / module_name),
                        parentpath,
                    )

                    zf.write(filepath, arcname)

    def _add_scenario_files_to_zipfile(self, zf: zipfile.ZipFile, data: dict):
        """Add scenario template files to the ZIP archive.

        :param zf: ZipFile object to write to
        :param data: Export data containing scenarios list
        """
        for scenario in data.get("scenarios", []):
            scenario_name = scenario["name"]
            scenario_dir = self.paths.scenario_global / scenario_name

            if not scenario_dir.exists():
                continue

            # Add all files in scenario directory to ZIP
            for dirpath, _, filenames in os.walk(scenario_dir):
                for filename in filenames:
                    filepath = Path(dirpath) / filename
                    parentpath = os.path.relpath(filepath, scenario_dir)
                    arcname = os.path.join("scenario", scenario_name, parentpath)
                    zf.write(filepath, arcname)

    def export_project(self, project_name: str, output_zip_name: str):
        """Export project configuration files.

        Generate a ZIP archive.

        :param project_name: Project name or the instance.
        :type project_name: str | Project
        :param output_file: Output filename.
        :type output_file: str
        :raises ProjectNotExistException: Project was not found.
        """
        project = self.prj_mgr.get_project(project_name)
        data = self._load_all_data_to_dict(project)

        with zipfile.ZipFile(output_zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
            # add database dump
            zf.writestr("database_dump.yaml", YamlParser.dump_data(data))
            self._add_user_files_to_zipfile(zf, data)
            self._add_module_files_to_zipfile(zf, data)
            self._add_scenario_files_to_zipfile(zf, data)

    def _apply_project_cluster_from_dump(
        self, prj: "project.Project", pc_data: dict | None
    ) -> None:
        if not pc_data or not pc_data.get("scenario_configs"):
            return
        pc = self.project_cluster_mgr.get_cluster(prj)
        for scenario_name, raw in pc_data["scenario_configs"].items():
            if not isinstance(raw, dict):
                continue
            sc = scenario_config_from_dict(scenario_name, raw)
            self.project_cluster_mgr.create_or_update_scenario_config(pc, sc)

    def _user_progress_from_import_dict(
        self, progress_dict: dict, failed_usernames: set[str]
    ) -> UserProgress:
        solved: dict[str, SolvedSecretRecord] = {}
        for cid, raw in (progress_dict.get("solved_secrets") or {}).items():
            if not isinstance(raw, dict):
                continue
            ref_name = raw.get("user")
            if ref_name and ref_name in failed_usernames:
                uid = None
            elif ref_name:
                uid = self.user_mgr.get_user(ref_name).id
            else:
                uid = None
            solved[str(cid)] = SolvedSecretRecord(
                cluster_kind=raw["cluster_kind"],
                scenario_name=raw["scenario_name"],
                local_name=raw["local_name"],
                submitted_at=parser.parse(raw["submitted_at"]),
                user_id=uid,
                value_at_submit=raw.get("value_at_submit"),
            )
        log: list[SecretSubmissionLogEntry] = []
        for entry in progress_dict.get("submission_log") or []:
            if not isinstance(entry, dict):
                continue
            log.append(
                SecretSubmissionLogEntry(
                    value=entry["value"],
                    timestamp=parser.parse(entry["timestamp"]),
                )
            )
        return UserProgress(
            solved_secrets=solved,
            submission_log=log,
            found_secrets=progress_dict["found_secrets"],
            last_submit_time=(
                parser.parse(progress_dict["last_submit_time"])
                if progress_dict.get("last_submit_time")
                else None
            ),
        )

    def _validate_with_database(self, data: DatabaseDumpDict):
        # check if they exist in the database, raise collision error if needed
        project = data["project"]
        if self.prj_mgr.get_doc_by_filter(name=project["name"]):
            raise ProjectExistsException(f"Project `{project['name']}` already exists.")
        modules = list(self.module_mgr.list_modules().keys())
        for module_name in data.get("modules", []):
            if module_name in modules:
                self.logger.warning(
                    f"Module `{module_name}` is already present on the host.",
                )
        usernames = [
            user["username"]
            for user in self.user_mgr.get_docs_raw(
                filter={
                    "username": {"$in": [user["username"] for user in data["users"]]}
                },
                projection={"_id": 0, "username": 1},
            )
        ]
        if usernames:
            raise UserExistsException(
                f"Users `{' '.join(usernames)}` already exist in the database."
            )

    @staticmethod
    def _run_coroutine_safely(coro):
        """Run async code from sync context (works when an event loop is already running)."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()

    def _remove_user_if_unenrolled(self, username: str) -> None:
        """Drop user document and global user dir when they have no enrollments."""
        user = self.user_mgr.get_doc_by_filter(username=username)
        if not user:
            return
        if self.enroll_mgr.collection.count_documents({"user_id.$id": user.id}) > 0:
            return
        up = self.paths.user_path(username)
        if up.exists():
            shutil.rmtree(up)
        self.user_mgr.remove_doc_by_id(user.id)

    def _revert_setup_new_user(self, username: str) -> None:
        """Remove user row and share dir after failed setup user creation."""
        self._remove_user_if_unenrolled(username)
        if not self.user_mgr.get_doc_by_filter(username=username):
            orphan = self.paths.user_path(username)
            if orphan.exists():
                shutil.rmtree(orphan)

    def _enrollment_active_exists(self, username: str, project_name: str) -> bool:
        user = self.user_mgr.get_doc_by_filter(username=username)
        project = self.prj_mgr.get_doc_by_filter(name=project_name)
        if not user or not project:
            return False
        return (
            self.enroll_mgr.get_doc_by_filter(
                **{"user_id.$id": user.id, "project_id.$id": project.id, "active": True}
            )
            is not None
        )

    def _cleanup_orphan_enrolled_path(self, username: str, project_name: str) -> None:
        user = self.user_mgr.get_doc_by_filter(username=username)
        project = self.prj_mgr.get_doc_by_filter(name=project_name)
        if not user or not project:
            return
        ep = self.paths.enrolled_user_path(user, project)
        if ep.exists():
            shutil.rmtree(ep)

    def _revert_setup_enrollment_slice(self, username: str, project_name: str) -> None:
        """Undo enroll_user_to_project via cancel_enrollment; fall back to DB/path-only cleanup."""
        try:
            self._run_coroutine_safely(
                self.enroll_mgr.cancel_enrollment(username, project_name)
            )
        except Exception:
            self._revert_imported_user_slice(username, project_name)
            return
        self._remove_user_if_unenrolled(username)

    def _revert_imported_user_slice(self, username: str, project_name: str) -> None:
        """Remove enrollment row + enrolled tree (import has no user cluster yet)."""
        user = self.user_mgr.get_doc_by_filter(username=username)
        project = self.prj_mgr.get_doc_by_filter(name=project_name)
        if user and project:
            enrollment = self.enroll_mgr.get_doc_by_filter(
                **{"user_id.$id": user.id, "project_id.$id": project.id}
            )
            if enrollment:
                self.enroll_mgr.remove_doc_by_id(enrollment.id)
            enrolled_path = self.paths.enrolled_user_path(user, project)
            if enrolled_path.exists():
                shutil.rmtree(enrolled_path)
        self._remove_user_if_unenrolled(username)

    def _add_to_database(self, data: DatabaseDumpDict) -> set[str]:
        """Insert dump rows; return usernames that failed and must not receive archive files."""
        failed_usernames: set[str] = set()
        # project and project cluster import
        p = data["project"]
        prj = self.prj_mgr.init_project(
            p["name"],
            p["max_nof_users"],
            starting_port_bind=p.get("starting_port_bind", -1),
            description=p.get("description", ""),
        )
        self._apply_project_cluster_from_dump(prj, data.get("project_cluster"))

        # user import
        for user in data["users"]:
            username = user["username"]
            try:
                self.user_mgr.create_and_insert_doc(**user)
            except Exception as e:
                self.logger.warning(
                    f"Import project: skipped user {username!r} after user insert "
                    f"failure: {e}"
                )
                failed_usernames.add(username)

        # enrollment and progress progress
        # TODO: imported objects should be related to the project
        for enrollment in data["enrollments"]:
            username = enrollment["user"]
            project_name = enrollment["project"]
            if username in failed_usernames:
                continue
            try:
                progress_dict = enrollment["progress"]
                progress = self._user_progress_from_import_dict(
                    progress_dict, failed_usernames
                )
                self.enroll_mgr.import_enrollment(username, project_name, progress)
            except Exception as e:
                self.logger.warning(
                    f"Import project: skipped user {username!r} after enrollment "
                    f"failure: {e}"
                )
                self._revert_imported_user_slice(username, project_name)
                failed_usernames.add(username)

        # user cluster import
        for cluster_data in data.get("clusters") or []:
            ref = cluster_data["enrollment_ref"]
            user_name, proj_name = ref.split("@", 1)
            if user_name in failed_usernames:
                continue
            try:
                user_obj = self.user_mgr.get_user(user_name)
                project_obj = self.prj_mgr.get_project(proj_name)
                enrollment_obj = self.enroll_mgr.get_enrollment(user_obj, project_obj)
                builder = UserCluster.Builder(cluster_data["name"], enrollment_obj)
                for scenario_name, raw in cluster_data.get(
                    "scenario_configs", {}
                ).items():
                    if not isinstance(raw, dict):
                        continue
                    builder.add_scenario_config(
                        scenario_name,
                        scenario_config_from_dict(scenario_name, raw),
                    )
                self.user_cluster_mgr.create_cluster(builder.build())
            except Exception as e:
                self.logger.warning(
                    f"Import project: skipped cluster for user {user_name!r} "
                    f"(project {proj_name!r}): {e}"
                )

        return failed_usernames

    def import_project(self, input_file: Path):
        """Import the project data from the zip file.

        The zipfile must contain a `database_dump.yaml` configuration, a directory
        containing all the modules used in the project, and a directory with user's
        shadow files. If a module already exists, the module will not be imported.

        :param input_file: A ZIP file containing project data.
        :type input_file: Path
        """
        with tempfile.TemporaryDirectory() as tempdir:
            dir_path = Path(tempdir)
            with zipfile.ZipFile(input_file, "r") as zf:
                if "database_dump.yaml" not in zf.namelist():
                    raise ImportFileCorruptedException(
                        "Missing `database_dump.yaml` file in the zip."
                    )

                with zf.open("database_dump.yaml") as f:
                    try:
                        data = cast(
                            DatabaseDumpDict,
                            YamlParser.load_data_stream(f, "database_dump"),
                        )
                    except ValidationError as e:
                        raise ImportFileCorruptedException(
                            "File `database_dump.yaml` does not match the schema.\n"
                            f"{str(e)}"
                        )

                # DB first: collisions abort; partial per-user failures recorded in set
                self._validate_with_database(data)
                failed_usernames = self._add_to_database(data)

                zf.extractall(dir_path)

                # Copy trees from temp extract into share roots (user shadows skip failures)
                # Archive paths use directory basename (e.g. share/user → "user")
                users_dir = dir_path / self.paths.user_global.name
                if users_dir.exists():
                    for item in users_dir.iterdir():
                        if item.name in failed_usernames:
                            continue
                        copytree(item, self.paths.user_global / item.name)

                modules_dir = dir_path / self.paths.module_global.name
                if modules_dir.exists():
                    for item in modules_dir.iterdir():
                        if not (self.paths.module_global / item.name).exists():
                            copytree(item, self.paths.module_global / item.name)

                scenario_dir = dir_path / "scenario"
                if scenario_dir.exists():
                    for item in scenario_dir.iterdir():
                        if not (self.paths.scenario_global / item.name).exists():
                            copytree(item, self.paths.scenario_global / item.name)

    def _dry_run_setup(self, data: SetupDict):
        out = {}
        # Report which project names from YAML are not yet in Mongo
        if data.get("projects"):
            project_names = [prj["name"] for prj in data["projects"]]
            found_names = [
                prj["name"]
                for prj in self.prj_mgr.get_docs_raw(
                    {"name": {"$in": project_names}}, {"_id": 0, "name": 1}
                )
            ]
            new_names = set(project_names).difference(set(found_names))
            if new_names:
                out["new_projects"] = list(new_names)

        # Same for usernames
        if data.get("users"):
            user_names = [user["username"] for user in data["users"]]
            found_names = [
                user["username"]
                for user in self.user_mgr.get_docs_raw(
                    {"username": {"$in": user_names}}, {"_id": 0, "username": 1}
                )
            ]
            new_names = set(user_names).difference(set(found_names))
            if new_names:
                out["new_users"] = list(new_names)
        if out:
            self.logger.print(YamlParser.dump_data(out))

    def _run_setup(self, data: SetupDict, exist_ok: bool) -> list[NewUserDict]:
        new_users = []
        failed_setup_usernames: set[str] = set()
        cluster_key = "cluster.scenario_configs"
        # project and project cluster
        if data.get("projects"):
            for prj_data in data["projects"]:
                prj_data = dict(prj_data)
                scenarios = prj_data.pop(cluster_key, {}) or {}
                try:
                    prj = self.prj_mgr.init_project(**prj_data)
                except ProjectExistsException as e:
                    if exist_ok:
                        self.logger.warning(str(e))
                        continue
                    raise ProjectExistsException(e)
                pc = self.project_cluster_mgr.get_cluster(prj)
                for scenario_name, raw in scenarios.items():
                    if not isinstance(raw, dict):
                        continue
                    sc = scenario_config_from_dict(scenario_name, raw)
                    self.project_cluster_mgr.create_or_update_scenario_config(pc, sc)

        # user
        if data.get("users"):
            for user in data["users"]:
                username = user["username"]
                try:
                    if user.get("generate_password"):
                        password = AuthInterface.generate_password(
                            DEFAULT_PASSWORD_LENGTH
                        )
                        _, user_data = self.user_mgr.create_new_user(
                            **user, password=password
                        )
                    else:
                        _, user_data = self.user_mgr.create_new_user(**user)
                except UserExistsException as e:
                    if exist_ok:
                        self.logger.warning(str(e))
                        continue
                    raise UserExistsException(e)
                except Exception as e:
                    self._revert_setup_new_user(username)
                    self.logger.warning(
                        f"Setup: skipped user {username!r} after user creation failure: {e}"
                    )
                    failed_setup_usernames.add(username)
                    continue
                new_users.append(user_data)

        # enrollments, progerss, user clusters
        if data.get("enrollments"):
            for enroll_data in data["enrollments"]:
                username = enroll_data["user"]
                project_name = enroll_data["project"]
                if username in failed_setup_usernames:
                    continue
                had_enrollment = self._enrollment_active_exists(username, project_name)
                try:
                    enroll_copy = dict(enroll_data)
                    uc_scenarios = enroll_copy.pop(cluster_key, {}) or {}
                    enrollment = self.enroll_mgr.enroll_user_to_project(
                        enroll_copy["user"], enroll_copy["project"]
                    )
                    enrollment.progress = self._user_progress_from_import_dict(
                        enroll_copy["progress"], failed_setup_usernames
                    )
                    self.enroll_mgr.update_doc(enrollment)
                    # Optional extra scenarios on the enrollment's UserCluster
                    uc = self.user_cluster_mgr.get_cluster(enrollment)
                    for scenario_name, raw in uc_scenarios.items():
                        if not isinstance(raw, dict):
                            continue
                        sc = scenario_config_from_dict(scenario_name, raw)
                        self.user_cluster_mgr.create_or_update_scenario_config(uc, sc)
                except Exception as e:
                    # Compare before/after to avoid reverting pre-existing enrollments
                    has_enrollment = self._enrollment_active_exists(
                        username, project_name
                    )
                    if has_enrollment and not had_enrollment:
                        self._revert_setup_enrollment_slice(username, project_name)
                    elif not has_enrollment and not had_enrollment:
                        self._cleanup_orphan_enrolled_path(username, project_name)

                    if isinstance(e, CTFBaseException):
                        if exist_ok:
                            self.logger.warning(str(e))
                            continue
                        raise CTFBaseException(e)
                    self.logger.warning(
                        f"Setup: skipped enrollment for {username!r} / "
                        f"{project_name!r}: {e}"
                    )
                    continue
        return new_users

    def setup_env_from_file(
        self, file: Path, exist_ok: bool = False, dry_run: bool = False
    ) -> list[NewUserDict]:
        """Run setup commands from YAML config file.

        The configuration file must follow the schema `setup.yaml`.

        :param file: A path to the YAML configuration file.
        :type file: Path
        :param exist_ok: Ignores collision and will only produce warning. Defaults to False.
        :type exist_ok: bool
        :param dry_run: Only simulates running the command. Defaults to False.
        :type dry_run: bool
        :return: A list of new users.
        :rtype: list[NewUserDict]
        """
        data: SetupDict = cast(SetupDict, YamlParser.load_data_file(file, "setup"))
        if dry_run:
            self._dry_run_setup(data)
            return []
        return self._run_setup(data, exist_ok)

    def uninstall(self):
        raise NotImplementedError()
