"""Shared repository for entity lookups across managers."""

from typing import TYPE_CHECKING

from bson import ObjectId
from pymongo.database import Database

from fit_ctf.models.utils.exceptions import (
    ProjectNotExistException,
    UserNotEnrolledToProjectException,
    UserNotExistsException,
)

if TYPE_CHECKING:
    from fit_ctf.models.core.enrollment import Enrollment
    from fit_ctf.models.core.project import Project
    from fit_ctf.models.core.user import User


class EntityRepository:
    """Shared repository for basic entity lookups.

    Provides common CRUD operations for User, Project, and Enrollment entities
    to eliminate circular dependencies between managers.
    """

    def __init__(self, db: Database):
        """Initialize EntityRepository.

        :param db: MongoDB database instance
        :type db: Database
        """
        self._db = db

    def get_user(self, user_or_username: "str | User", active: bool | None = True) -> "User":
        """Retrieve a user from the database.

        :param user_or_username: User username or user object.
        :type user_or_username: str | User
        :param active: Fetch documents with the given active value. If set to None,
            the function fetches both active and inactive documents. Defaults to True.
        :type active: bool | None
        :raises UserNotExistsException: User with the given username was not found.
        :return: A found user object.
        :rtype: User
        """
        from fit_ctf.models.core.user import User

        if isinstance(user_or_username, User):
            return user_or_username

        username = user_or_username
        filter_: dict = {"username": username}
        if active is not None:
            filter_["active"] = active

        user = self._db["user"].find_one(filter_)
        if not user:
            raise UserNotExistsException(f"User `{username}` does not exist.")
        return User(**user)

    def get_project(
        self, project_or_name: "str | Project", active: bool | None = True
    ) -> "Project":
        """Retrieve project data from the database.

        :param project_or_name: Project name or project object.
        :type project_or_name: str | Project
        :param active: Fetch documents with the given active value. If set to None,
            the function fetches both active and inactive documents. Defaults to True.
        :type active: bool | None
        :raises ProjectNotExistException: Project data was not found in the database.
        :return: Found project object.
        :rtype: Project
        """
        from fit_ctf.models.core.project import Project

        if isinstance(project_or_name, Project):
            return project_or_name

        project_name = project_or_name
        filter_: dict = {"name": project_name}
        if active is not None:
            filter_["active"] = active

        prj = self._db["project"].find_one(filter_)
        if not prj:
            raise ProjectNotExistException(f"Project `{project_name}` does not exist.")
        return Project(**prj)

    def get_enrollment(
        self, user: "User", project: "Project", active: bool | None = True
    ) -> "Enrollment":
        """Get an enrollment document for user-project pair.

        :param user: User object.
        :type user: User
        :param project: Project object.
        :type project: Project
        :param active: Fetch documents with the given active value.
        :type active: bool | None
        :raises UserNotEnrolledToProjectException: User is not enrolled to project.
        :return: The found enrollment document.
        :rtype: Enrollment
        """
        from fit_ctf.models.core.enrollment import Enrollment

        filter_: dict = {
            "user_id.$id": user.id,
            "project_id.$id": project.id,
        }
        if active is not None:
            filter_["active"] = active

        enrollment = self._db["enrollment"].find_one(filter_)
        if not enrollment:
            raise UserNotEnrolledToProjectException(
                f"User `{user.username}` is not enrolled to project `{project.name}`."
            )
        return Enrollment(**enrollment)

    def get_user_by_id(self, user_id: ObjectId) -> "User":
        """Get user by ObjectId.

        :param user_id: User ObjectId
        :type user_id: ObjectId
        :return: User object
        :rtype: User
        :raises UserNotExistsException: If user not found
        """
        from fit_ctf.models.core.user import User

        user = self._db["user"].find_one({"_id": user_id})
        if not user:
            raise UserNotExistsException(f"User {user_id} does not exist.")
        return User(**user)

    def get_project_by_id(self, project_id: ObjectId) -> "Project":
        """Get project by ObjectId.

        :param project_id: Project ObjectId
        :type project_id: ObjectId
        :return: Project object
        :rtype: Project
        :raises ProjectNotExistException: If project not found
        """
        from fit_ctf.models.core.project import Project

        project = self._db["project"].find_one({"_id": project_id})
        if not project:
            raise ProjectNotExistException(f"Project {project_id} does not exist.")
        return Project(**project)

    def get_enrollment_by_id(self, enrollment_id: ObjectId) -> "Enrollment":
        """Get enrollment by ObjectId.

        :param enrollment_id: Enrollment ObjectId
        :type enrollment_id: ObjectId
        :return: Enrollment object
        :rtype: Enrollment
        :raises EnrollmentNotExistException: If enrollment not found
        """
        from fit_ctf.models.core.enrollment import Enrollment
        from fit_ctf.models.utils.exceptions import EnrollmentNotExistException

        enrollment = self._db["enrollment"].find_one({"_id": enrollment_id})
        if not enrollment:
            raise EnrollmentNotExistException(f"Enrollment {enrollment_id} not found.")
        return Enrollment(**enrollment)
