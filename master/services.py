from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from .persistence.repositories import (
    DesiredStateRepository,
    ServiceAssignmentRepository,
    WorkerNodeRepository,
)


@dataclass(frozen=True)
class PlacementResult:
    assignment_id: str
    worker_node_id: str
    desired_version: int


class MasterPlacementService:
    """Application boundary for an atomic placement change."""

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def place(
        self,
        service_id: str,
        worker_node_id: str,
        allocation: dict[str, Any],
        lifecycle_state: str,
        configuration: dict[str, Any],
        assignment_status: str = "ASSIGNED",
    ) -> PlacementResult:
        with self.session_factory() as session:
            with session.begin():
                worker_node = WorkerNodeRepository(session).reserve_capacity(
                    worker_node_id, allocation
                )
                assignment = ServiceAssignmentRepository(session).create_or_replace(
                    service_id, worker_node.id, assignment_status
                )
                desired_version = DesiredStateRepository(session).put_next(
                    service_id, lifecycle_state, configuration
                )

                return PlacementResult(
                    assignment_id=assignment.id,
                    worker_node_id=worker_node.id,
                    desired_version=desired_version,
                )