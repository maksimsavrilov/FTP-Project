from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ActualState, DesiredState, ServiceAssignment, WorkerNode


def _normalize_id(value: uuid.UUID | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    return str(value)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: datetime | str | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(timezone.utc)


class WorkerNodeRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, node_id):
        return self.session.get(WorkerNode, _normalize_id(node_id))

    def list(self, status: str | None = None, capability: str | None = None):
        query = select(WorkerNode)
        if status:
            query = query.where(WorkerNode.status == status)
        rows = self.session.execute(query).scalars().all()
        if capability:
            return [row for row in rows if row.capabilities and capability in row.capabilities]
        return rows

    def create(self, node: WorkerNode):
        node.id = _normalize_id(node.id) or str(uuid.uuid4())
        self.session.add(node)
        self.session.flush()
        return node

    def update_health(self, node_id, status: str, usage: dict[str, Any], last_heartbeat_at):
        node = self.session.execute(
            select(WorkerNode).where(WorkerNode.id == _normalize_id(node_id)).with_for_update()
        ).scalar_one_or_none()
        if node is None:
            raise LookupError(f"WorkerNode {node_id} not found")

        node.status = status
        node.cpu_usage = float(usage.get("cpu", node.cpu_usage or 0))
        node.memory_usage = int(usage.get("memory", node.memory_usage or 0))
        node.disk_usage = int(usage.get("disk", node.disk_usage or 0))
        node.last_heartbeat_at = _parse_datetime(last_heartbeat_at) or _utcnow()
        node.updated_at = _utcnow()
        self.session.flush()
        return node

    def reserve_capacity(self, node_id, allocation: dict[str, Any]):
        node = self.session.execute(
            select(WorkerNode).where(WorkerNode.id == _normalize_id(node_id)).with_for_update()
        ).scalar_one_or_none()
        if node is None:
            raise LookupError(f"WorkerNode {node_id} not found")

        requested_cpu = float(allocation.get("cpu", 0))
        requested_memory = int(allocation.get("memory", 0))
        requested_disk = int(allocation.get("disk", 0))

        if node.cpu_usage + requested_cpu > node.cpu_capacity:
            raise ValueError("CPU capacity exceeded")
        if node.memory_usage + requested_memory > node.memory_capacity:
            raise ValueError("Memory capacity exceeded")
        if node.disk_usage + requested_disk > node.disk_capacity:
            raise ValueError("Disk capacity exceeded")

        node.cpu_usage += requested_cpu
        node.memory_usage += requested_memory
        node.disk_usage += requested_disk
        node.updated_at = _utcnow()
        self.session.flush()
        return node

    def decommission(self, node_id):
        node = self.session.execute(
            select(WorkerNode).where(WorkerNode.id == _normalize_id(node_id)).with_for_update()
        ).scalar_one_or_none()
        if node is None:
            raise LookupError(f"WorkerNode {node_id} not found")

        active = self.session.execute(
            select(ServiceAssignment).where(
                ServiceAssignment.worker_node_id == _normalize_id(node_id),
                ServiceAssignment.status.in_(["ASSIGNED", "DRAINING"]),
            )
        ).scalars().all()
        if active:
            raise ValueError("Cannot decommission a node with active assignments")

        node.status = "DECOMMISSIONED"
        node.updated_at = _utcnow()
        self.session.flush()
        return node


class ServiceAssignmentRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_active_for_service(self, service_id):
        return self.session.execute(
            select(ServiceAssignment).where(
                ServiceAssignment.service_id == _normalize_id(service_id),
                ServiceAssignment.status.in_(["ASSIGNED", "DRAINING"]),
            ).with_for_update()
        ).scalars().first()

    def list_for_node(self, node_id, active_only: bool = True):
        query = select(ServiceAssignment).where(ServiceAssignment.worker_node_id == _normalize_id(node_id))
        if active_only:
            query = query.where(ServiceAssignment.status.in_(["ASSIGNED", "DRAINING"]))
        return self.session.execute(query).scalars().all()

    def create_or_replace(self, service_id, worker_node_id, status: str):
        normalized_service_id = _normalize_id(service_id)
        normalized_node_id = _normalize_id(worker_node_id)

        existing = self.get_active_for_service(normalized_service_id)
        current_time = _utcnow()
        if existing:
            existing.status = "RELEASED"
            existing.released_at = current_time
            existing.updated_at = current_time

        assignment = ServiceAssignment(
            service_id=normalized_service_id,
            worker_node_id=normalized_node_id,
            status=status,
            assigned_at=current_time,
            released_at=None,
            created_at=current_time,
            updated_at=current_time,
        )
        self.session.add(assignment)
        self.session.flush()
        return assignment

    def release(self, assignment_id):
        assignment = self.session.get(ServiceAssignment, _normalize_id(assignment_id))
        if assignment is None:
            raise LookupError(f"ServiceAssignment {assignment_id} not found")
        assignment.status = "RELEASED"
        assignment.released_at = _utcnow()
        assignment.updated_at = _utcnow()
        self.session.flush()
        return assignment

    def validate_current(self, service_id, assignment_id):
        active = self.get_active_for_service(service_id)
        return bool(active and _normalize_id(active.id) == _normalize_id(assignment_id))


class DesiredStateRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, service_id):
        return self.session.get(DesiredState, _normalize_id(service_id))

    def put_next(self, service_id, lifecycle_state: str, configuration: dict[str, Any]):
        service_id = _normalize_id(service_id)
        now = _utcnow()
        current = self.session.execute(
            select(DesiredState).where(DesiredState.service_id == service_id).with_for_update()
        ).scalar_one_or_none()
        if current is None:
            next_version = 1
            state = DesiredState(
                service_id=service_id,
                version=next_version,
                lifecycle_state=lifecycle_state,
                configuration=configuration or {},
                updated_at=now,
            )
            self.session.add(state)
            self.session.flush()
            return next_version

        next_version = int(current.version) + 1
        current.version = next_version
        current.lifecycle_state = lifecycle_state
        current.configuration = configuration or {}
        current.updated_at = now
        self.session.flush()
        return next_version

    def get_for_reconciliation(self, service_id):
        desired = self.get(service_id)
        assignment = ServiceAssignmentRepository(self.session).get_active_for_service(service_id)
        return desired, assignment


class ActualStateRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, service_id):
        return self.session.get(ActualState, _normalize_id(service_id))

    def record_observation(self, service_id, assignment_id, version: int, status: str, configuration: dict[str, Any], health: dict[str, Any], observed_at):
        normalized_service_id = _normalize_id(service_id)
        normalized_assignment_id = _normalize_id(assignment_id)

        assignment_ok = ServiceAssignmentRepository(self.session).validate_current(normalized_service_id, normalized_assignment_id)
        if not assignment_ok:
            raise ValueError("Assignment does not match the current active assignment")

        existing = self.session.execute(
            select(ActualState).where(ActualState.service_id == normalized_service_id).with_for_update()
        ).scalar_one_or_none()
        observed_dt = _parse_datetime(observed_at) or _utcnow()

        if existing is not None and int(existing.version) > int(version):
            return False
        if existing is not None and int(existing.version) == int(version) and observed_dt <= existing.observed_at:
            return False

        record = existing or ActualState(service_id=normalized_service_id)
        record.version = int(version)
        record.status = status
        record.configuration = configuration or {}
        record.health = health or {}
        record.observed_at = observed_dt
        record.updated_at = _utcnow()
        if existing is None:
            self.session.add(record)
        self.session.flush()
        return True
