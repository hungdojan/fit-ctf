from datetime import datetime
from typing import Any, Literal

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field


class SolvedSecretRecord(BaseModel):
    """One correctly submitted flag, keyed by composite id in UserProgress.solved_secrets."""

    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True)

    cluster_kind: Literal["user", "project"]
    scenario_name: str
    local_name: str
    submitted_at: datetime
    user_id: ObjectId | None = None
    value_at_submit: str | None = None

    def model_dump(self, by_alias: bool = True, **kw) -> dict[str, Any]:
        return super().model_dump(by_alias=by_alias, **kw)


class SecretSubmissionLogEntry(BaseModel):
    """Raw submission attempt (value + time only)."""

    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True)

    value: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now().astimezone())

    def model_dump(self, by_alias: bool = True, **kw) -> dict[str, Any]:
        return super().model_dump(by_alias=by_alias, **kw)
