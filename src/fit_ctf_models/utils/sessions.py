from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class ProgressSession(BaseModel):
    class State(str, Enum):
        START = "START"
        STOP = "STOP"

    timestamp: datetime
    state: State
    info: dict[str, Any] = {}


class LoginSession(BaseModel):
    class State(str, Enum):
        LOGIN = "LOGIN"
        LOGOUT = "LOGOUT"

    timestamp: datetime
    state: State
    info: dict[str, Any] = {}
