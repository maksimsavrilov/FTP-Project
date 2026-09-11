from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from .persistence.repositories import (
    ActualStateRepository,
    DesiredStateRepository,
    ServiceAssignmentRepository,
    WorkerNodeRepository,
)


@dataclass(frozen=True)
class PlacementResult:
    assignment_id: str
    worker_node_id: str
    desired_version: int


@dataclass(frozen=True)
class ActualStateReportResult:
    accepted: bool


@dataclass(frozen=True)
class ReconciliationState:
    desired: Any
    assignment: Any
    actual: Any


class MasterNodeService:
    """Application boundary for node reads and heartbeat updates."""

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def get(self, node_id: str):
        with self.session_factory() as session:
            return WorkerNodeRepository(session).get(node_id)

    def list(self, status: str | None = None, capability: str | None = None):
        with self.session_factory() as session:
            return WorkerNodeRepository(session).list(status, capability)

    def heartbeat(
        self,
        node_id: str,
        status: str,
        usage: dict[str, Any],
        last_heartbeat_at: Any,
    ):
        with self.session_factory() as session:
            with session.begin():
                node = WorkerNodeRepository(session).update_health(
                    node_id, status, usage, last_heartbeat_at
                )
            session.refresh(node)
            return node


class MasterReconciliationService:
    """Application boundary for desired-state reads and agent reports."""

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def get_state(self, service_id: str) -> ReconciliationState:
        with self.session_factory() as session:
            desired, assignment = DesiredStateRepository(session).get_for_reconciliation(
                service_id
            )
            actual = ActualStateRepository(session).get(service_id)
            return ReconciliationState(desired, assignment, actual)

    def report_actual_state(
        self,
        service_id: str,
        assignment_id: str,
        version: int,
        status: str,
        configuration: dict[str, Any],
        health: dict[str, Any],
        observed_at: Any,
    ) -> ActualStateReportResult:
        with self.session_factory() as session:
            with session.begin():
                accepted = ActualStateRepository(session).record_observation(
                    service_id,
                    assignment_id,
                    version,
                    status,
                    configuration,
                    health,
                    observed_at,
                )
                return ActualStateReportResult(accepted=accepted)


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