"""Shared document fields for user and project cluster models."""

from pydantic import Field

from fit_ctf_models.base import Base
from fit_ctf_models.clusters.config_models import ScenarioConfig


class ClusterDocument(Base):
    """Base for cluster documents with scenario configuration (DB + compile)."""

    name: str
    scenario_configs: dict[str, ScenarioConfig] = Field(default_factory=dict)
    scenario_names: list[str] = Field(default_factory=list)
