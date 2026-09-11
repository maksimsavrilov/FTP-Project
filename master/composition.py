from __future__ import annotations

import os
from collections.abc import Callable

from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .api import MasterApi
from .auth import AuthenticationClient
from .fastapi import create_app
from .services import (
    MasterDatabaseServiceService,
    MasterDatabaseUserService,
    MasterDnsServiceService,
    MasterDomainService,
    MasterMailAccountService,
    MasterMailDomainService,
    MasterMailServiceService,
    MasterNodeService,
    MasterReconciliationService,
    MasterServicePlanService,
    MasterServiceService,
    MasterSubscriptionService,
    MasterUserService,
    MasterWebsiteService,
    MasterWebServiceService,
)


SessionFactory = Callable[[], Session]


def build_master_api(
    session_factory: SessionFactory,
    authentication_client: AuthenticationClient,
) -> MasterApi:
    """Assemble the Master application boundary from its production dependencies."""

    return MasterApi(
        MasterNodeService(session_factory),
        MasterReconciliationService(session_factory),
        authorization_client=authentication_client,
        user_service=MasterUserService(session_factory),
        service_plan_service=MasterServicePlanService(session_factory),
        subscription_service=MasterSubscriptionService(session_factory),
        domain_service=MasterDomainService(session_factory),
        website_service=MasterWebsiteService(session_factory),
        service_service=MasterServiceService(session_factory),
        web_service_service=MasterWebServiceService(session_factory),
        dns_service_service=MasterDnsServiceService(session_factory),
        mail_service_service=MasterMailServiceService(session_factory),
        database_service_service=MasterDatabaseServiceService(session_factory),
        database_user_service=MasterDatabaseUserService(session_factory),
        mail_domain_service=MasterMailDomainService(session_factory),
        mail_account_service=MasterMailAccountService(session_factory),
    )


def create_master_app(
    database_url: str | None = None,
    auth_service_url: str | None = None,
    *,
    engine_factory: Callable[..., Engine] = create_engine,
) -> FastAPI:
    """Create the production Master FastAPI application.

    Configuration defaults to DATABASE_URL and AUTH_SERVICE_URL so the same
    composition root can be used by a container entrypoint or a test.
    """

    database_url = database_url or os.environ.get("DATABASE_URL")
    auth_service_url = auth_service_url or os.environ.get("AUTH_SERVICE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    if not auth_service_url:
        raise RuntimeError("AUTH_SERVICE_URL is required")

    engine = engine_factory(database_url)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    api = build_master_api(session_factory, AuthenticationClient(auth_service_url))
    return create_app(api)
