from datetime import datetime

from bson import DBRef, ObjectId
from pymongo.database import Database

import fit_ctf.ctf_base as ctf_base
import fit_ctf_models.project as _prj
from fit_ctf_models.secret import Secret
import fit_ctf_models.user as _user
from fit_ctf_components.exceptions import (
    SecretAlreadyExistsException,
    SecretNotFoundException,
    UserProgressNotExistException,
)
from fit_ctf_models.base import Base, BaseManagerInterface


class UserProgress(Base):
    user_id: DBRef
    project_id: DBRef
    secrets: dict[str, Secret]


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

    def get_user_progress(
        self, user: "_user.User", project: "_prj.Project"
    ) -> UserProgress | None:
        return self.get_doc_by_filter(
            **{"user_id.$id": user.id, "project_id.$id": project.id, "active": True}
        )

    def generate_secrets(self, data: str, user: "_user.User", project: "_prj.Project"):
        secret = self.ctf_base.secret_mgr.generate_hash(data, user, project)
        up = self.get_user_progress(user, project)
        if not up:
            raise UserProgressNotExistException(
                "Could not find the user progress document."
            )
        if secret in up.secrets:
            raise SecretAlreadyExistsException(
                "The secret hash is already set for this user."
            )
        up.secrets[secret] = Secret(value=secret)

    def get_secret_state(
        self, secret: str, user: "_user.User", project: "_prj.Project"
    ) -> Secret:
        up = self.get_user_progress(user, project)
        if not up:
            raise UserProgressNotExistException(
                "Could not find the user progress document."
            )

        if secret not in up.secrets:
            raise SecretNotFoundException("Given secret is not located in the storage.")
        return up.secrets[secret]

    def update_secret_state(
        self,
        secret: str,
        user: "_user.User",
        project: "_prj.Project",
        time: datetime | None,
    ):
        up = self.get_user_progress(user, project)
        if not up:
            raise UserProgressNotExistException(
                "Could not find the user progress document."
            )

        if secret not in up.secrets:
            raise SecretNotFoundException("Given secret is not located in the storage.")
        up.secrets[secret].submited = time
