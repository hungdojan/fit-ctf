"""
Composite secret ids and flattening UserCluster + ProjectCluster secrets for submission.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from fit_ctf.models.infra.config_models import ScenarioConfig

if TYPE_CHECKING:
    import fit_ctf.models.infra.project_cluster as project_cluster
    import fit_ctf.models.infra.user_cluster as user_cluster


ClusterKind = Literal["user", "project"]

COMPOSITE_SEP = "\x1f"


def composite_secret_id(
    cluster_kind: ClusterKind, scenario_name: str, local_name: str
) -> str:
    return COMPOSITE_SEP.join((cluster_kind, scenario_name, local_name))


def parse_composite_secret_id(composite_id: str) -> tuple[ClusterKind, str, str]:
    parts = composite_id.split(COMPOSITE_SEP, 2)
    if len(parts) != 3:
        raise ValueError(f"Invalid composite secret id: {composite_id!r}")
    kind, scenario, local = parts
    if kind not in ("user", "project"):
        raise ValueError(f"Invalid cluster kind in composite id: {kind!r}")
    return kind, scenario, local


def format_composite_for_display(composite_id: str) -> str:
    return composite_id.replace(COMPOSITE_SEP, "/")


def flatten_scenario_secrets(
    cluster_kind: ClusterKind,
    scenario_configs: dict[str, ScenarioConfig],
) -> dict[str, str]:
    """Map composite_id -> expected secret string (opaque; may be human-chosen or random)."""
    out: dict[str, str] = {}
    for scenario_name, cfg in scenario_configs.items():
        for local_name, val in cfg.secrets.items():
            cid = composite_secret_id(cluster_kind, scenario_name, local_name)
            out[cid] = val
    return out


def merged_submission_secret_map(
    user_cluster: "user_cluster.UserCluster | None",
    project_cluster: "project_cluster.ProjectCluster | None",
) -> dict[str, str]:
    m: dict[str, str] = {}
    if project_cluster is not None:
        m.update(flatten_scenario_secrets("project", project_cluster.scenario_configs))
    if user_cluster is not None:
        m.update(flatten_scenario_secrets("user", user_cluster.scenario_configs))
    return m


def count_submittable_secret_slots(
    user_cluster: "user_cluster.UserCluster | None",
    project_cluster: "project_cluster.ProjectCluster | None",
) -> int:
    return len(merged_submission_secret_map(user_cluster, project_cluster))
