import os.path
from pathlib import Path
from typing import TypedDict


class LeaderboardDataTableItem(TypedDict):
    position: int
    username: str
    found_secrets: int
    last_submit_time: str
    percentage_score: str


def get_resource_dir() -> Path:
    return Path(os.path.dirname(os.path.realpath(__file__))) / "resources"
