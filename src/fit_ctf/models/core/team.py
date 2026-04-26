from bson import ObjectId
from pydantic import Field

from fit_ctf.models.base import Base, BaseManagerInterface
from fit_ctf.models.core.user import User


class UserAlreadyInTeam(Exception):
    pass


class TeamAlreadyExistError(Exception):
    pass


class TeamNotFoundError(Exception):
    pass


class Team(Base):
    name: str
    user_ids: list[ObjectId] = Field(default_factory=list)


class TeamManager(BaseManagerInterface[Team]):
    def get_team(self, team_or_name: str | Team) -> Team:
        if isinstance(team_or_name, Team):
            return team_or_name
        team = self.get_doc_by_filter(name=team_or_name)
        if not team:
            raise TeamNotFoundError()
        return team

    def create_team(self, name: str) -> Team:
        team = self.get_doc_by_filter(name=name)
        if team:
            raise TeamAlreadyExistError()
        team = self.create_and_insert_doc(name=name)
        return team

    def add_user(self, team_or_name: str | Team, user: User):
        team = self.get_team(team_or_name)
        if user.id in team.user_ids:
            raise UserAlreadyInTeam()
        team.user_ids.append(user.id)
        self.update_doc(team)

    def remove_user(self, team_or_name: str | Team, user: User):
        team = self.get_team(team_or_name)
        if user.id not in set(team.user_ids):
            return
        team.user_ids.remove(user.id)
        self.update_doc(team)

    def rename_team(self, team: Team, name: str):
        team.name = name
        self.update_doc(team)

    def delete_team(self, team_or_name: str | Team):
        team = self.get_team(team_or_name)
        self.remove_doc_by_id(team.id)
