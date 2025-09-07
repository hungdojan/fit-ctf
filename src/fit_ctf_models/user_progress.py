from datetime import datetime
from typing import Literal, overload

from bson import DBRef, ObjectId
from bson.binary import Binary
from pymongo.database import Database

import fit_ctf.ctf_base as ctf_base
import fit_ctf_models.project as _prj
import fit_ctf_models.user as _user
from fit_ctf_components.types import SecretInfo
from fit_ctf_models.base import Base, BaseManagerInterface
from fit_ctf_models.secret import Secret, SecretManager
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
        """Return the list of stored secrets."""
        return [
            {"name": name, "submitted": secret.submitted}
            for name, secret in self.secrets.items()
        ]

    def get_secret_by_value(self, search_index: str) -> Secret | None:
        """Search for a stored secret by its value.

        :param secret_value: The encrypted secret value.
        :type secret_value: str
        :return: Found secret, None if not found.
        :rtype: Secret | None
        """
        for secret in self.secrets.values():
            if secret.search_index == search_index:
                return secret
        return None

    def get_secret_by_name(self, name: str) -> Secret | None:
        """Return a secret based on the name.

        :param name: Secret identification name.
        :type name: str
        :return: Found secret, None if not found.
        :rtype: Secret | None
        """
        return self.secrets.get(name, None)

    def get_last_submit(self) -> datetime | None:
        """Get the date of the last submitted secret.

        :return: Timestamp of the last submitted secret. None if no secret was found.
        :rtype: datetime | None
        """
        submitted: list[datetime] = [
            sec.submitted for sec in self.secrets.values() if sec.submitted is not None
        ]
        if not submitted:
            return None
        return sorted(submitted, reverse=True)[0]


class UserProgressManager(BaseManagerInterface[UserProgress], SecretManager):

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

    # secrets

    def add_secret(self, doc: UserProgress, name: str, value: str) -> None:
        """Adds a secret to the list of secrets.

        :param doc: Secret map document.
        :type doc: UserProgress
        :param name: The identification name of the secret.
        :type name: str
        :param value: The value of the secret.
        :type value: str
        :raises SecretAlreadyExistsException:
            The secret with the given name already exist in the database.
        """
        if doc.secrets.get(name):
            raise SecretAlreadyExistsException(f"Secret `{name}` already exists.")

        search_index = self.compute_search_index(value)
        nonce, ct = self.encrypt(value)
        doc.secrets[name] = Secret(
            **{
                "search_index": search_index,
                "nonce": Binary(nonce),
                "enc_secret": Binary(ct),
                "submitted": None,
                "user_id": None,
            }
        )
        self.update_doc(doc)

    def update_secret_value(self, doc: UserProgress, name: str, value: str) -> None:
        """Update a secret value.

        Does not save the document.
        :param doc: Secret map document.
        :type doc: UserProgress
        :param name: The identification name of the secret.
        :type name: str
        :param value: The value of the secret.
        :type value: str
        :raises SecretNotFoundException: When the secret was not found in the list.
        """
        if not doc.secrets.get(name):
            raise SecretNotFoundException(f"Secret `{name}` not found.")

        nonce, ct = self.encrypt(value)
        doc.secrets[name].nonce = Binary(nonce)
        doc.secrets[name].enc_secret = Binary(ct)
        self.update_doc(doc)

    def get_secret_by_value(self, doc: UserProgress, value: str) -> Secret | None:
        """Retrieve a secret object from the document.

        :param doc: Secret map document.
        :type doc: UserProgress
        :param value: The value of the secret.
        :type value: str
        """
        return doc.get_secret_by_value(self.compute_search_index(value))

    def submit_secret(self, doc: UserProgress, value: str, user: "_user.User"):
        """Tries to submit a secret.

        Raises exceptions if the secret is not found or was already submitted.
        If the function passes, both Secret and UserProgress instances were updated
        but are NOT SAVED IN THE DATABASE.
        :param doc: Secret map document
        :type doc: UserProgress
        :param value: The value of the secret.
        :type value: str
        :param user: The user object that submitted the secret.
        :type user: _user.User
        :raises SecretNotFoundException: When the secret was not found in the list.
        :raises SecretAlreadySubmittedException: When the secret was already submitted in the past.
        """
        secret = doc.get_secret_by_value(self.compute_search_index(value))
        if not secret:
            raise SecretNotFoundException("Submitted secret not found.")
        if secret.submitted is not None:
            raise SecretAlreadySubmittedException("This secret was already submitted")

        secret.submitted = datetime.now()
        secret.user_id = user.id
        doc.found_secrets += 1
        doc.last_submit_time = secret.submitted
        self.update_doc(doc)

    def delete_secret(
        self, doc: UserProgress, name: str, ignore_missing: bool = True
    ) -> None:
        """Remove the secret from the list.

        :param doc: Secret map document.
        :type doc: UserProgress
        :param name: The identification name of the secret.
        :type name: str
        :param value: The value of the secret.
        :type value: str
        """
        if not doc.secrets.get(name):
            if not ignore_missing:
                raise SecretNotFoundException(f"Secret `{name}` not found.")
            return

        secret = doc.secrets.pop(name)
        if secret.submitted is not None:
            doc.found_secrets -= 1
            doc.last_submit_time = doc.get_last_submit()
        self.update_doc(doc)

    def fetch_leaderboard(self, project: "_prj.Project", nof_users: int) -> list[dict]:
        pipeline = MongoQueries.fetch_leaderboard(project, nof_users)
        return [item for item in self.collection.aggregate(pipeline)]
