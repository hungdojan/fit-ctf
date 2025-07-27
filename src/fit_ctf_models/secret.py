from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class Secret(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, use_enum_values=True)
    name: str
    value: str
    submitted: datetime | None = None

    def model_dump(self, by_alias: bool = True, **kw) -> dict[str, Any]:
        return super().model_dump(by_alias=by_alias, **kw)
