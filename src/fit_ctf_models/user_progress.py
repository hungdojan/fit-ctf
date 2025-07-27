from datetime import datetime
from typing import Literal, overload

from bson import DBRef, ObjectId
from pymongo.database import Database

import fit_ctf.ctf_base as ctf_base
import fit_ctf_models.project as _prj
import fit_ctf_models.user as _user
from fit_ctf_components.types import SecretInfo
from fit_ctf_models.base import Base, BaseManagerInterface
from fit_ctf_models.secret import Secret
from fit_ctf_models.utils.exceptions import (
    SecretAlreadyExistsException,
    SecretAlreadySubmittedException,
    SecretNotFoundException,
    UserProgressNotExistException,
)
from fit_ctf_models.utils.mongo_queries import MongoQueries


class UserProgress(Base):
    user_id: DBRef
    project_id: DBRef
    secrets: dict[str, Secret]
    found_secrets: int
    last_submit_time: datetime | None

    def list_secrets(self) -> list[SecretInfo]:
        return [
            {"name": secret.name, "submitted": secret.submitted}
            for secret in self.secrets.values()
        ]

    def get_secret_by_value(self, secret_value: str) -> Secret | None:
        found_secret = [
            secret for secret in self.secrets.values() if secret.value == secret_value
        ]
        return found_secret[0] if found_secret else None

    def get_secret_by_name(self, name: str) -> Secret | None:
        return self.secrets.get(name, None)


class UserProgressManager(BaseManagerInterface[UserProgress]):

    def __init__(self, ctf_base: "ctf_base.CTFBase", db: Database):
        super().__init__(ctf_base, db, db["user_progress"])

    def get_doc_by_id(self, _id: ObjectId) -> UserProgress | None:
        res = self._coll.find_one({"_id": _id})
        return UserProgress(**res) if res else None

    def get_doc_by_id_raw(self, _id: ObjectId, projection: dict | None = None):
        projection = {} if projection is None else projection
        return self._coll.find_one({"_id": _id}, projection=projection)

    def get_doc_by_filter(self, **kw) -> UserProgress | None:
        res = self._coll.find_one(filter=kw)
        return UserProgress(**res) if res else None

    def get_doc_by_filter_raw(
        self, filter: dict | None = None, projection: dict | None = None
    ):
        filter = {} if filter is None else filter
        projection = {} if projection is None else projection
        return self._coll.find_one(filter=filter, projection=projection)

    def get_docs(self, **filter) -> list[UserProgress]:
        res = self._coll.find(filter=filter)
        return [UserProgress(**data) for data in res]

    def create_and_insert_doc(self, **kw) -> UserProgress:
        doc = UserProgress(**kw)
        self._coll.insert_one(doc.model_dump())
        return doc

    @overload
    def get_user_progress(
        self, user: "_user.User", project: "_prj.Project", ignore_missing: Literal[True]
    ) -> UserProgress | None: ...

    @overload
    def get_user_progress(
        self,
        user: "_user.User",
        project: "_prj.Project",
        ignore_missing: Literal[False] = False,
    ) -> UserProgress: ...

    def get_user_progress(
        self, user: "_user.User", project: "_prj.Project", ignore_missing: bool = False
    ) -> UserProgress | None:
        up = self.get_doc_by_filter(
            **{"user_id.$id": user.id, "project_id.$id": project.id, "active": True}
        )
        if not up and not ignore_missing:
            raise UserProgressNotExistException(
                "Could not find the user progress document."
            )
        return up

    def generate_secrets(self, name: str, user: "_user.User", project: "_prj.Project"):
        up = self.get_user_progress(user, project)
        if name in up.secrets:
            raise SecretAlreadyExistsException(
                "The secret hash is already set for this user."
            )

        secret = self.ctf_base.secret_mgr.generate_hash(name, user, project)
        up.secrets[name] = Secret(name=name, value=secret)

    def list_secrets(
        self, user: "_user.User", project: "_prj.Project"
    ) -> list[SecretInfo]:
        up = self.get_user_progress(user, project)
        return up.list_secrets()

    def submit_secret(self, secret: str, user: "_user.User", project: "_prj.Project"):
        up = self.get_user_progress(user, project)
        s = up.get_secret_by_value(secret)
        if not s:
            raise SecretNotFoundException("Given secret is not located in the storage")
        if s.submitted is not None:
            raise SecretAlreadySubmittedException("The secret was already submitted.")
        s.submitted = datetime.now()
        # count a total of found secrets
        up.found_secrets = len(
            [secret for secret in up.secrets.values() if secret.submitted is not None]
        )
        up.last_submit_time = s.submitted
        self.update_doc(up)

    def sync_secrets(self, project: "_prj.Project"):
        for up in self.get_docs(**{"project_id.$id": project.id}):
            found_secrets = [
                secret for secret in up.secrets.values() if secret.submitted is not None
            ]

            # no secrets where found set default values
            if found_secrets == 0:
                up.found_secrets = 0
                up.last_submit_time = None
                self.update_doc(up)
                continue

            # sync found secrets, update only when data are misaligned
            found_secrets = sorted(
                found_secrets, key=lambda x: x.submitted or 0, reverse=True
            )
            if (
                up.found_secrets != len(found_secrets)
                or up.last_submit_time != found_secrets[0].submitted
            ):
                up.found_secrets = len(found_secrets)
                up.last_submit_time = found_secrets[0].submitted
                self.update_doc(up)

    def fetch_leaderboard(self, project: "_prj.Project", nof_users: int) -> list[dict]:
        pipeline = MongoQueries.fetch_leaderboard(project, nof_users)
        return [item for item in self.collection.aggregate(pipeline)]
