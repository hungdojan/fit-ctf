from datetime import datetime
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict


class Secret(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True)
    value: str
    submitted: datetime | None = None
    user_id: ObjectId | None = None

    def model_dump(self, by_alias: bool = True, **kw) -> dict[str, Any]:
        return super().model_dump(by_alias=by_alias, **kw)
