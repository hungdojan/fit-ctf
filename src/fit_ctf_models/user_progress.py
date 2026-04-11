from datetime import datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from fit_ctf_components.base import BaseComponent
from fit_ctf_components.types import SecretInfo
from fit_ctf_models.clusters.secret_slots import (
    format_composite_for_display,
    merged_submission_secret_map,
    parse_composite_secret_id,
)
from fit_ctf_models.secret import SecretSubmissionLogEntry, SolvedSecretRecord
from fit_ctf_models.utils.exceptions import (
    SecretAlreadySubmittedException,
    SecretNotFoundException,
)
from fit_ctf_models.utils.sessions import ProgressSession

if TYPE_CHECKING:
    import fit_ctf.ctf_base as ctf_base
    import fit_ctf_models.enrollment as enroll


class UserProgress(BaseModel):
    solved_secrets: dict[str, SolvedSecretRecord] = Field(default_factory=dict)
    submission_log: list[SecretSubmissionLogEntry] = Field(default_factory=list)
    found_secrets: int = 0
    last_submit_time: datetime | None = None
    sessions: list[ProgressSession] = Field(default_factory=list)


class UserProgressManager(BaseComponent):
    def __init__(self, ctf_base: "ctf_base.CTFBase"):
        super().__init__(ctf_base)

    def _clusters_for_submission(self, enrollment: "enroll.Enrollment"):
        from fit_ctf_models.utils.exceptions import ProjectClusterNotExistException

        user_cluster = self.ctf_base.user_cluster_mgr.get_doc_by_filter(
            **{"enrollment_id.$id": enrollment.id}
        )
        project = self.ctf_base.prj_mgr.get_doc_by_id(enrollment.project_id.id)
        project_cluster = None
        if project:
            try:
                project_cluster = self.ctf_base.project_cluster_mgr.get_cluster(project)
            except ProjectClusterNotExistException:
                project_cluster = None
        return user_cluster, project_cluster

    def submit_secret(self, enrollment: "enroll.Enrollment", value: str):
        """Validate submitted string against merged cluster secrets; log every attempt."""
        progress = enrollment.progress
        now = datetime.now().astimezone()
        progress.submission_log.append(
            SecretSubmissionLogEntry(value=value, timestamp=now)
        )

        user_cluster, project_cluster = self._clusters_for_submission(enrollment)
        merged = merged_submission_secret_map(user_cluster, project_cluster)
        matching = [cid for cid, expected in merged.items() if expected == value]
        if not matching:
            self.ctf_base.enroll_mgr.update_doc(enrollment)
            raise SecretNotFoundException("Submitted secret not found.")

        composite_id = sorted(matching)[0]
        if composite_id in progress.solved_secrets:
            self.ctf_base.enroll_mgr.update_doc(enrollment)
            raise SecretAlreadySubmittedException("This secret was already submitted")

        kind, scenario_name, local_name = parse_composite_secret_id(composite_id)
        progress.solved_secrets[composite_id] = SolvedSecretRecord(
            cluster_kind=kind,
            scenario_name=scenario_name,
            local_name=local_name,
            submitted_at=now,
            user_id=enrollment.user_id.id,
            value_at_submit=value,
        )
        progress.found_secrets = len(progress.solved_secrets)
        progress.last_submit_time = now
        self.ctf_base.enroll_mgr.update_doc(enrollment)

    def list_secrets_for_display(
        self, enrollment: "enroll.Enrollment", show_flag: bool = False
    ) -> list[SecretInfo]:
        user_cluster, project_cluster = self._clusters_for_submission(enrollment)
        merged = merged_submission_secret_map(user_cluster, project_cluster)
        solved = enrollment.progress.solved_secrets
        items: list[SecretInfo] = []
        for composite_id in sorted(merged.keys()):
            rec = solved.get(composite_id)
            items.append(
                {
                    "name": format_composite_for_display(composite_id),
                    "submitted": rec.submitted_at if rec else None,
                    "flag": merged[composite_id] if show_flag else None,
                }
            )
        return items

    def count_submittable_slots(self, enrollment: "enroll.Enrollment") -> int:
        user_cluster, project_cluster = self._clusters_for_submission(enrollment)
        return len(merged_submission_secret_map(user_cluster, project_cluster))

    def record_session(
        self,
        enrollment: "enroll.Enrollment",
        state: ProgressSession.State,
        info: dict[str, Any] = {},
    ):
        timestamp = datetime.now().astimezone()
        enrollment.progress.sessions.append(
            ProgressSession(timestamp=timestamp, state=state, info=info)
        )
        self.ctf_base.enroll_mgr.update_doc(enrollment)
