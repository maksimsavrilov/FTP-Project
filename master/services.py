from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from .persistence.repositories import (
    ActualStateRepository,
    DesiredStateRepository,
    DomainRepository,
    ServiceAssignmentRepository,
    ServicePlanRepository,
    ServiceRepository,
    SubscriptionRepository,
    UserRepository,
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


@dataclass(frozen=True)
class UserResult:
    id: str
    status: str
    created_at: Any
    updated_at: Any


@dataclass(frozen=True)
class ServicePlanResult:
    id: str
    name: str
    status: str
    resource_limits: dict[str, Any]
    object_limits: dict[str, Any]
    created_at: Any
    updated_at: Any


@dataclass(frozen=True)
class SubscriptionResult:
    id: str
    user_id: str
    plan_id: str
    status: str
    created_at: Any
    expires_at: Any


@dataclass(frozen=True)
class DomainResult:
    id: str
    subscription_id: str
    name: str
    status: str
    created_at: Any


@dataclass(frozen=True)
class ServiceResult:
    id: str
    subscription_id: str
    type: str
    status: str
    created_at: Any
    updated_at: Any
    assignment_id: str
    worker_node_id: str
    assignment_status: str
    desired_version: int
    lifecycle_state: str
    configuration: dict[str, Any]
    desired_updated_at: Any


class MasterUserService:
    """Application boundary for user lifecycle operations."""

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def get(self, user_id: str):
        with self.session_factory() as session:
            user = UserRepository(session).get(user_id)
            if user is None:
                raise LookupError(f"User {user_id} not found")
            return user

    def create(self, status: str = "ACTIVE"):
        with self.session_factory() as session:
            with session.begin():
                user = UserRepository(session).create(status)
                return UserResult(user.id, user.status, user.created_at, user.updated_at)


class MasterServicePlanService:
    """Application boundary for service plan lifecycle operations."""

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def get(self, plan_id: str):
        with self.session_factory() as session:
            plan = ServicePlanRepository(session).get(plan_id)
            if plan is None:
                raise LookupError(f"ServicePlan {plan_id} not found")
            return plan

    def create(
        self,
        name: str,
        status: str = "ACTIVE",
        resource_limits: dict[str, Any] | None = None,
        object_limits: dict[str, Any] | None = None,
    ):
        with self.session_factory() as session:
            with session.begin():
                plan = ServicePlanRepository(session).create(
                    name, status, resource_limits, object_limits
                )
                return ServicePlanResult(
                    plan.id,
                    plan.name,
                    plan.status,
                    plan.resource_limits,
                    plan.object_limits,
                    plan.created_at,
                    plan.updated_at,
                )


class MasterSubscriptionService:
    """Application boundary for subscription lifecycle operations."""

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def get(self, subscription_id: str):
        with self.session_factory() as session:
            subscription = SubscriptionRepository(session).get(subscription_id)
            if subscription is None:
                raise LookupError(f"Subscription {subscription_id} not found")
            return subscription

    def create(
        self,
        user_id: str,
        plan_id: str,
        status: str = "ACTIVE",
        expires_at: str | None = None,
    ):
        with self.session_factory() as session:
            with session.begin():
                if UserRepository(session).get(user_id) is None:
                    raise LookupError(f"User {user_id} not found")
                if ServicePlanRepository(session).get(plan_id) is None:
                    raise LookupError(f"ServicePlan {plan_id} not found")
                subscription = SubscriptionRepository(session).create(
                    user_id, plan_id, status, expires_at
                )
                return SubscriptionResult(
                    subscription.id,
                    subscription.user_id,
                    subscription.plan_id,
                    subscription.status,
                    subscription.created_at,
                    subscription.expires_at,
                )


class MasterDomainService:
    """Application boundary for domain lifecycle operations."""

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def get(self, domain_id: str):
        with self.session_factory() as session:
            domain = DomainRepository(session).get(domain_id)
            if domain is None:
                raise LookupError(f"Domain {domain_id} not found")
            return domain

    def create(
        self,
        subscription_id: str,
        name: str,
        status: str = "PENDING",
    ):
        with self.session_factory() as session:
            with session.begin():
                if SubscriptionRepository(session).get(subscription_id) is None:
                    raise LookupError(f"Subscription {subscription_id} not found")
                domain = DomainRepository(session).create(subscription_id, name, status)
                return DomainResult(
                    domain.id,
                    domain.subscription_id,
                    domain.name,
                    domain.status,
                    domain.created_at,
                )


class MasterServiceService:
    """Application boundary for service creation, placement, and reads."""

    SUPPORTED_TYPES = {"WEB", "DNS", "MAIL", "DATABASE"}

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def get(self, service_id: str):
        with self.session_factory() as session:
            service = ServiceRepository(session).get(service_id)
            if service is None:
                raise LookupError(f"Service {service_id} not found")
            desired, assignment = DesiredStateRepository(session).get_for_reconciliation(service_id)
            if desired is None or assignment is None:
                raise LookupError(f"Placement state for Service {service_id} not found")
            return ServiceResult(
                service.id,
                service.subscription_id,
                service.type,
                service.status,
                service.created_at,
                service.updated_at,
                assignment.id,
                assignment.worker_node_id,
                assignment.status,
                desired.version,
                desired.lifecycle_state,
                desired.configuration or {},
                desired.updated_at,
            )

    def create(
        self,
        subscription_id: str,
        service_type: str,
        allocation: dict[str, Any],
        lifecycle_state: str,
        configuration: dict[str, Any],
    ):
        with self.session_factory() as session:
            with session.begin():
                if SubscriptionRepository(session).get(subscription_id) is None:
                    raise LookupError(f"Subscription {subscription_id} not found")
                if service_type not in self.SUPPORTED_TYPES:
                    raise ValueError(f"Unsupported service type: {service_type}")

                service = ServiceRepository(session).create(
                    subscription_id, service_type, lifecycle_state
                )
                candidates = WorkerNodeRepository(session).list(
                    status="ONLINE", capability=service_type.lower()
                )
                worker_node = None
                for candidate in candidates:
                    try:
                        worker_node = WorkerNodeRepository(session).reserve_capacity(
                            candidate.id, allocation
                        )
                        break
                    except ValueError:
                        continue
                if worker_node is None:
                    raise ValueError("No worker node available for service placement")

                assignment = ServiceAssignmentRepository(session).create_or_replace(
                    service.id, worker_node.id, "ASSIGNED"
                )
                DesiredStateRepository(session).put_next(
                    service.id, lifecycle_state, configuration
                )
                desired = DesiredStateRepository(session).get(service.id)
                return ServiceResult(
                    service.id,
                    service.subscription_id,
                    service.type,
                    service.status,
                    service.created_at,
                    service.updated_at,
                    assignment.id,
                    assignment.worker_node_id,
                    assignment.status,
                    desired.version,
                    desired.lifecycle_state,
                    desired.configuration or {},
                    desired.updated_at,
                )


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