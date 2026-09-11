from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ActualState, DesiredState, DnsService, Domain, Service, ServiceAssignment, ServicePlan, Subscription, User, Website, WebService, WorkerNode


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


class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, user_id):
        return self.session.get(User, _normalize_id(user_id))

    def create(self, status: str = "ACTIVE"):
        user = User(status=status)
        self.session.add(user)
        self.session.flush()
        return user


class ServicePlanRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, plan_id):
        return self.session.get(ServicePlan, _normalize_id(plan_id))

    def create(
        self,
        name: str,
        status: str = "ACTIVE",
        resource_limits: dict[str, Any] | None = None,
        object_limits: dict[str, Any] | None = None,
    ):
        plan = ServicePlan(
            name=name,
            status=status,
            resource_limits=resource_limits or {},
            object_limits=object_limits or {},
        )
        self.session.add(plan)
        self.session.flush()
        return plan


class SubscriptionRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, subscription_id):
        return self.session.get(Subscription, _normalize_id(subscription_id))

    def create(
        self,
        user_id: str,
        plan_id: str,
        status: str = "ACTIVE",
        expires_at: datetime | str | None = None,
    ):
        subscription = Subscription(
            user_id=_normalize_id(user_id),
            plan_id=_normalize_id(plan_id),
            status=status,
            expires_at=_parse_datetime(expires_at),
        )
        self.session.add(subscription)
        self.session.flush()
        return subscription


class ServiceRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, service_id):
        return self.session.get(Service, _normalize_id(service_id))

    def create(self, subscription_id: str, service_type: str, status: str = "PENDING"):
        service = Service(
            subscription_id=_normalize_id(subscription_id),
            type=service_type,
            status=status,
        )
        self.session.add(service)
        self.session.flush()
        return service


class DomainRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, domain_id):
        return self.session.get(Domain, _normalize_id(domain_id))

    def create(self, subscription_id: str, name: str, status: str = "PENDING"):
        domain = Domain(
            subscription_id=_normalize_id(subscription_id),
            name=name,
            status=status,
        )
        self.session.add(domain)
        self.session.flush()
        return domain


class WebsiteRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, website_id):
        return self.session.get(Website, _normalize_id(website_id))

    def create(self, domain_id: str, document_root: str, status: str = "PENDING"):
        website = Website(
            domain_id=_normalize_id(domain_id),
            document_root=document_root,
            status=status,
        )
        self.session.add(website)
        self.session.flush()
        return website


class WebServiceRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, service_id):
        return self.session.get(WebService, _normalize_id(service_id))

    def create(
        self,
        service_id: str,
        website_id: str,
        web_server: str,
        php_version: str,
        document_root: str,
    ):
        web_service = WebService(
            service_id=_normalize_id(service_id),
            website_id=_normalize_id(website_id),
            web_server=web_server,
            php_version=php_version,
            document_root=document_root,
        )
        self.session.add(web_service)
        self.session.flush()
        return web_service


class DnsServiceRepository:
    def __init__(self, session: Session):
        self.session = session

    def get(self, service_id):
        return self.session.get(DnsService, _normalize_id(service_id))

    def create(self, service_id: str):
        dns_service = DnsService(service_id=_normalize_id(service_id))
        self.session.add(dns_service)
        self.session.flush()
        return dns_service


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

        requested_cpu = Decimal(str(allocation.get("cpu", 0)))
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
        existing_observed_at = _parse_datetime(existing.observed_at) if existing else None
        if existing is not None and int(existing.version) == int(version) and observed_dt <= existing_observed_at:
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
