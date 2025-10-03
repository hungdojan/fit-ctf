from datetime import datetime

from pydantic import BaseModel

import fit_ctf.ctf_base as ctf_base
import fit_ctf_models.user_enrollment as _ue
from fit_ctf_components.base import BaseComponent
from fit_ctf_components.types import SecretInfo
from fit_ctf_models.secret import Secret, SecretManager
from fit_ctf_models.utils.exceptions import (
    SecretAlreadySubmittedException,
    SecretNameAlreadyExistsException,
    SecretNotFoundException,
    SecretValueCollision,
)


class UserProgress(BaseModel):
    secrets: dict[str, Secret] = {}
    found_secrets: int = 0
    last_submit_time: datetime | None = None

    def get_secret_by_value(self, value: str) -> Secret | None:
        """Retrieve a secret object from the document.

        :param value: The value of the secret.
        :type value: str
        :return: Found secret object, None if not found.
        :rtype: Secret | None
        """
        search_index = SecretManager.compute_search_index(value)
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

    def list_secrets(self) -> list[SecretInfo]:
        """Return the list of stored secrets."""
        return [
            {"name": name, "submitted": secret.submitted}
            for name, secret in self.secrets.items()
        ]

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


class UserProgressManager(BaseComponent):
    def __init__(self, ctf_base: "ctf_base.CTFBase"):
        super().__init__(ctf_base)

    def add_secret(self, ue: "_ue.UserEnrollment", name: str, value: str) -> Secret:
        """Adds a secret to the list of secrets.

        :param ue: Base User enrollment document.
        :type ue: _ue.UserEnrollment
        :param name: The identification name of the secret.
        :type name: str
        :param value: The value of the secret.
        :type value: str
        :raises SecretNameAlreadyExistsException:
            The secret with the given name already exists in the progress doc.
        :raises SecretValueCollision:
            The secret with the given value already exists in the progress doc.
        :return: Created secret.
        :rtype: Secret
        """
        progress = ue.progress
        if progress.secrets.get(name):
            raise SecretNameAlreadyExistsException(
                f"Secret with name `{name}` already exists."
            )
        if progress.get_secret_by_value(value):
            raise SecretValueCollision("Secret with given value already exists.")

        search_index = SecretManager.compute_search_index(value)
        nonce, ct = SecretManager.encrypt(value)
        secret = Secret(
            **{
                "search_index": search_index,
                "nonce": nonce,
                "enc_secret": ct,
                "submitted": None,
                "user_id": None,
            }
        )
        progress.secrets[name] = secret
        self.ctf_base.ue_mgr.update_doc(ue)
        return secret

    def update_secret_value(
        self,
        ue: "_ue.UserEnrollment",
        name: str,
        value: str,
        override_submit: bool = False,
    ) -> None:
        """Update a secret value.

        :param ue: Base User enrollment document.
        :type ue: _ue.UserEnrollment
        :param name: The identification name of the secret.
        :type name: str
        :param value: The value of the secret.
        :type value: str
        :param override_submit: If secret was submitted, this update will nullify it.
            Defaults to False.
        :type override_submit: bool
        :raises SecretNotFoundException: When the secret was not found in the list.
        :raises SecretValueCollision:
            The secret with the given value already exists in the progress doc.
        """
        progress = ue.progress
        if not progress.secrets.get(name):
            raise SecretNotFoundException(f"Secret `{name}` not found.")
        if progress.get_secret_by_value(value):
            raise SecretValueCollision("Secret with given value already exists.")

        search_index = SecretManager.compute_search_index(value)
        nonce, ct = SecretManager.encrypt(value)
        progress.secrets[name].nonce = nonce
        progress.secrets[name].enc_secret = ct
        progress.secrets[name].search_index = search_index

        # nullify a secret stats if "updated" secret is changed
        if override_submit and progress.secrets[name].submitted:
            progress.secrets[name].submitted = None
            progress.found_secrets -= 1
            progress.last_submit_time = progress.get_last_submit()

        self.ctf_base.ue_mgr.update_doc(ue)

    def submit_secret(self, ue: "_ue.UserEnrollment", value: str):
        """Tries to submit a secret.

        Raises exceptions if the secret is not found or was already submitted.
        If the function passes, the document is saved.
        :param ue: Base User enrollment document.
        :type ue: _ue.UserEnrollment
        :param value: The value of the secret.
        :type value: str
        :raises SecretNotFoundException: When the secret was not found in the list.
        :raises SecretAlreadySubmittedException: When the secret was already submitted in the past.
        """
        progress = ue.progress
        secret = progress.get_secret_by_value(value)
        if not secret:
            raise SecretNotFoundException("Submitted secret not found.")
        if secret.submitted is not None:
            raise SecretAlreadySubmittedException("This secret was already submitted")

        secret.submitted = datetime.now().astimezone()
        secret.user_id = ue.user_id.id
        progress.found_secrets += 1
        progress.last_submit_time = secret.submitted
        self.ctf_base.ue_mgr.update_doc(ue)

    def delete_secret(
        self, ue: "_ue.UserEnrollment", name: str, ignore_missing: bool = True
    ) -> None:
        """Remove the secret from the list.

        :param ue: Base User enrollment document.
        :type ue: _ue.UserEnrollment
        :param name: The identification name of the secret.
        :type name: str
        :param ignore_missing: Does not raise Exception if secret is not found.
            Defaults to True.
        :type ignore_missing: bool
        :raises SecretNotFoundException: If ignore_missing is `False` and
            secret name is not in the collection.
        """
        progress = ue.progress
        if not progress.get_secret_by_name(name):
            if not ignore_missing:
                raise SecretNotFoundException(f"Secret `{name}` not found.")
            return

        secret = progress.secrets.pop(name)
        if secret.submitted is not None:
            progress.found_secrets -= 1
            progress.last_submit_time = progress.get_last_submit()
        self.ctf_base.ue_mgr.update_doc(ue)
