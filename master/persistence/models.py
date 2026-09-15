from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, JSON, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_status", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now())


class IdentityReference(Base):
    __tablename__ = "identity_references"
    __table_args__ = (UniqueConstraint("provider", "subject_id", name="uq_identity_references_provider_subject"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider: Mapped[str] = mapped_column(String, nullable=False)
    subject_id: Mapped[str] = mapped_column(String, nullable=False)


class Account(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        Index("ix_accounts_role", "role"),
        Index("ix_accounts_status", "status"),
        Index("ix_accounts_parent_account_id", "parent_account_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    identity_reference_id: Mapped[str | None] = mapped_column(String(36), nullable=True, unique=True)
    parent_account_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now())


class ServicePlan(Base):
    __tablename__ = "service_plans"
    __table_args__ = (Index("ix_service_plans_status", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    resource_limits: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    object_limits: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now())


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (Index("ix_subscriptions_user_id", "user_id"), Index("ix_subscriptions_status", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ResourceEntitlement(Base):
    __tablename__ = "resource_entitlements"
    __table_args__ = (
        UniqueConstraint("subscription_id", "resource_name", name="uq_resource_entitlements_subscription_resource"),
        Index("ix_resource_entitlements_subscription_id", "subscription_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subscription_id: Mapped[str] = mapped_column(String(36), nullable=False)
    resource_name: Mapped[str] = mapped_column(String, nullable=False)
    limit: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False)
    usage: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=0)
    reservation: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=4), nullable=False, default=0)
    source: Mapped[str] = mapped_column(String, nullable=False)


class Service(Base):
    __tablename__ = "services"
    __table_args__ = (
        Index("ix_services_subscription_id", "subscription_id"),
        Index("ix_services_type", "type"),
        Index("ix_services_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subscription_id: Mapped[str] = mapped_column(String(36), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now())


class Domain(Base):
    __tablename__ = "domains"
    __table_args__ = (Index("ix_domains_subscription_id", "subscription_id"), Index("ix_domains_status", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subscription_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())


class Website(Base):
    __tablename__ = "websites"
    __table_args__ = (Index("ix_websites_domain_id", "domain_id"), Index("ix_websites_status", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    domain_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    document_root: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())


class MailDomain(Base):
    __tablename__ = "mail_domains"
    __table_args__ = (Index("ix_mail_domains_domain_id", "domain_id"), Index("ix_mail_domains_status", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    domain_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())


class MailAccount(Base):
    __tablename__ = "mail_accounts"
    __table_args__ = (Index("ix_mail_accounts_mail_domain_id", "mail_domain_id"), Index("ix_mail_accounts_status", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mail_domain_id: Mapped[str] = mapped_column(String(36), nullable=False)
    address: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())


class WorkerNode(Base):
    __tablename__ = "worker_nodes"
    __table_args__ = (
        Index("ix_worker_nodes_status", "status"),
        Index("ix_worker_nodes_last_heartbeat_at", "last_heartbeat_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    hostname: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    capabilities: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    cpu_capacity: Mapped[float] = mapped_column(Numeric(precision=10, scale=2), nullable=False)
    memory_capacity: Mapped[int] = mapped_column(BigInteger, nullable=False)
    disk_capacity: Mapped[int] = mapped_column(BigInteger, nullable=False)
    cpu_usage: Mapped[float] = mapped_column(Numeric(precision=10, scale=2), nullable=False, default=0)
    memory_usage: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    disk_usage: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now())


class ServiceAssignment(Base):
    __tablename__ = "service_assignments"
    __table_args__ = (
        Index("ix_service_assignments_worker_node_status", "worker_node_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    service_id: Mapped[str] = mapped_column(String(36), nullable=False)
    worker_node_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now())


class DesiredState(Base):
    __tablename__ = "desired_states"

    service_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    lifecycle_state: Mapped[str] = mapped_column(String, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now())


class WebService(Base):
    __tablename__ = "web_services"

    service_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    website_id: Mapped[str] = mapped_column(String(36), nullable=False)
    web_server: Mapped[str] = mapped_column(String, nullable=False)
    php_version: Mapped[str] = mapped_column(String, nullable=False)
    document_root: Mapped[str] = mapped_column(String, nullable=False)


class DnsService(Base):
    __tablename__ = "dns_services"

    service_id: Mapped[str] = mapped_column(String(36), primary_key=True)


class MailService(Base):
    __tablename__ = "mail_services"

    service_id: Mapped[str] = mapped_column(String(36), primary_key=True)


class DatabaseService(Base):
    __tablename__ = "database_services"

    service_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    database_type: Mapped[str] = mapped_column(String, nullable=False)
    database_name: Mapped[str] = mapped_column(String, nullable=False)


class DatabaseUser(Base):
    __tablename__ = "database_users"
    __table_args__ = (
        Index("ix_database_users_database_service_id", "database_service_id"),
        Index("ix_database_users_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    database_service_id: Mapped[str] = mapped_column(String(36), nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    privileges: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class ActualState(Base):
    __tablename__ = "actual_states"

    service_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    health: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow, server_default=func.now())
