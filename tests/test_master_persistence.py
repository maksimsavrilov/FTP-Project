import unittest
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from master.persistence.models import Base, WorkerNode, ServiceAssignment, DesiredState, ActualState
from master.persistence.repositories import (
    AccountRepository,
    WorkerNodeRepository,
    ServiceAssignmentRepository,
    DesiredStateRepository,
    ActualStateRepository,
    IdentityReferenceRepository,
    ResourceEntitlementRepository,
)
from master.services import MasterNodeService, MasterPlacementService, MasterReconciliationService


class MasterPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.session = Session(self.engine)

        self.worker_repo = WorkerNodeRepository(self.session)
        self.assignment_repo = ServiceAssignmentRepository(self.session)
        self.desired_repo = DesiredStateRepository(self.session)
        self.actual_repo = ActualStateRepository(self.session)

    def tearDown(self):
        self.session.close()

    def test_worker_node_and_state_flow(self):
        node_id = uuid.uuid4()
        created = self.worker_repo.create(
            WorkerNode(
                id=node_id,
                hostname="node-1",
                status="ONLINE",
                capabilities={"web": True},
                cpu_capacity=8,
                memory_capacity=8192,
                disk_capacity=100000,
                cpu_usage=0,
                memory_usage=0,
                disk_usage=0,
            )
        )
        self.assertEqual(created.hostname, "node-1")

        updated = self.worker_repo.update_health(
            node_id,
            status="DEGRADED",
            usage={"cpu": 2, "memory": 3500, "disk": 5000},
            last_heartbeat_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(updated.status, "ONLINE")

        desired = self.desired_repo.put_next(
            "service-123",
            lifecycle_state="PROVISIONING",
            configuration={"web_server": "nginx"},
        )
        self.assertEqual(desired, 1)

        latest = self.desired_repo.get("service-123")
        self.assertEqual(latest.version, 1)

        assignment = self.assignment_repo.create_or_replace(
            service_id="service-123",
            worker_node_id=node_id,
            status="ASSIGNED",
        )
        self.assertEqual(assignment.status, "ASSIGNED")

        self.assertTrue(
            self.actual_repo.record_observation(
                service_id="service-123",
                assignment_id=assignment.id,
                version=1,
                status="RUNNING",
                configuration={"web_server": "nginx"},
                health={"ready": True},
                observed_at="2026-01-01T00:10:00Z",
            )
        )

        actual = self.actual_repo.get("service-123")
        self.assertEqual(actual.status, "RUNNING")
        self.assertEqual(actual.version, 1)

    def test_account_identity_and_subscription_entitlement_flow(self):
        identity = IdentityReferenceRepository(self.session).create("zitadel", "user-123")
        account = AccountRepository(self.session).create(
            role="CUSTOMER",
            identity_reference_id=identity.id,
        )
        entitlement = ResourceEntitlementRepository(self.session).create(
            subscription_id="subscription-123",
            resource_name="disk",
            limit=100,
            usage=20,
            reservation=10,
            source="SERVICE_PLAN",
        )
        self.session.commit()

        self.assertEqual(IdentityReferenceRepository(self.session).get_by_subject("zitadel", "user-123").id, identity.id)
        self.assertEqual(AccountRepository(self.session).get(account.id).role, "CUSTOMER")
        loaded = ResourceEntitlementRepository(self.session).get("subscription-123", "disk")
        self.assertEqual(loaded.limit, 100)
        self.assertEqual(loaded.usage + loaded.reservation, 30)

    def test_placement_service_replaces_assignment_and_increments_desired_state(self):
        node_id = str(uuid.uuid4())
        with self.session.begin():
            self.worker_repo.create(
                WorkerNode(
                    id=node_id,
                    hostname="node-1",
                    status="ONLINE",
                    capabilities={"web": True},
                    cpu_capacity=8,
                    memory_capacity=8192,
                    disk_capacity=100000,
                    cpu_usage=0,
                    memory_usage=0,
                    disk_usage=0,
                )
            )

        result = MasterPlacementService(lambda: Session(self.engine)).place(
            service_id="service-123",
            worker_node_id=node_id,
            allocation={"cpu": 2, "memory": 1024, "disk": 5000},
            lifecycle_state="PROVISIONING",
            configuration={"web_server": "nginx"},
        )
        replacement = MasterPlacementService(lambda: Session(self.engine)).place(
            service_id="service-123",
            worker_node_id=node_id,
            allocation={"cpu": 1, "memory": 512, "disk": 1000},
            lifecycle_state="RUNNING",
            configuration={"web_server": "nginx", "workers": 2},
        )

        with Session(self.engine) as session:
            assignment = ServiceAssignmentRepository(session).get_active_for_service("service-123")
            desired = DesiredStateRepository(session).get("service-123")
            node = WorkerNodeRepository(session).get(node_id)
            previous_assignment = session.get(ServiceAssignment, result.assignment_id)

        self.assertEqual(assignment.id, replacement.assignment_id)
        self.assertNotEqual(assignment.id, result.assignment_id)
        self.assertEqual(assignment.worker_node_id, node_id)
        self.assertEqual(previous_assignment.status, "RELEASED")
        self.assertEqual(desired.version, replacement.desired_version)
        self.assertEqual(desired.version, 2)
        self.assertEqual(node.cpu_usage, 3)

    def test_placement_service_rolls_back_capacity_and_assignment_on_failure(self):
        node_id = str(uuid.uuid4())
        with self.session.begin():
            self.worker_repo.create(
                WorkerNode(
                    id=node_id,
                    hostname="node-1",
                    status="ONLINE",
                    capabilities={"web": True},
                    cpu_capacity=1,
                    memory_capacity=8192,
                    disk_capacity=100000,
                    cpu_usage=0,
                    memory_usage=0,
                    disk_usage=0,
                )
            )

        with self.assertRaises(ValueError):
            MasterPlacementService(lambda: Session(self.engine)).place(
                service_id="service-123",
                worker_node_id=node_id,
                allocation={"cpu": 2, "memory": 1024, "disk": 5000},
                lifecycle_state="PROVISIONING",
                configuration={"web_server": "nginx"},
            )

        with Session(self.engine) as session:
            self.assertIsNone(DesiredStateRepository(session).get("service-123"))
            self.assertIsNone(ServiceAssignmentRepository(session).get_active_for_service("service-123"))
            self.assertEqual(WorkerNodeRepository(session).get(node_id).cpu_usage, 0)

    def test_node_service_updates_heartbeat(self):
        node_id = str(uuid.uuid4())
        with self.session.begin():
            self.worker_repo.create(
                WorkerNode(
                    id=node_id,
                    hostname="node-1",
                    status="ONLINE",
                    capabilities={"web": True},
                    cpu_capacity=8,
                    memory_capacity=8192,
                    disk_capacity=100000,
                    cpu_usage=0,
                    memory_usage=0,
                    disk_usage=0,
                )
            )

        node = MasterNodeService(lambda: Session(self.engine)).heartbeat(
            node_id,
            status="DEGRADED",
            usage={"cpu": 2, "memory": 3500, "disk": 5000},
            last_heartbeat_at="2026-01-01T00:10:00Z",
        )

        self.assertEqual(node.status, "ONLINE")
        self.assertEqual(node.memory_usage, 3500)

    def test_node_service_marks_stale_nodes_offline_but_preserves_disabled(self):
        with self.session.begin():
            self.worker_repo.create(
                WorkerNode(
                    hostname="stale-node",
                    status="ONLINE",
                    capabilities={},
                    cpu_capacity=1,
                    memory_capacity=1,
                    disk_capacity=1,
                    cpu_usage=0,
                    memory_usage=0,
                    disk_usage=0,
                    last_heartbeat_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                )
            )
            self.worker_repo.create(
                WorkerNode(
                    hostname="disabled-node",
                    status="DISABLED",
                    capabilities={},
                    cpu_capacity=1,
                    memory_capacity=1,
                    disk_capacity=1,
                    cpu_usage=0,
                    memory_usage=0,
                    disk_usage=0,
                    last_heartbeat_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                )
            )

        service = MasterNodeService(
            lambda: Session(self.engine),
            heartbeat_timeout=__import__("datetime").timedelta(seconds=60),
        )
        nodes = service.list()

        statuses = {node.hostname: node.status for node in nodes}
        self.assertEqual(statuses["stale-node"], "OFFLINE")
        self.assertEqual(statuses["disabled-node"], "DISABLED")

    def test_reconciliation_service_reports_and_reads_actual_state(self):
        node_id = str(uuid.uuid4())
        with self.session.begin():
            self.worker_repo.create(
                WorkerNode(
                    id=node_id,
                    hostname="node-1",
                    status="ONLINE",
                    capabilities={"web": True},
                    cpu_capacity=8,
                    memory_capacity=8192,
                    disk_capacity=100000,
                    cpu_usage=0,
                    memory_usage=0,
                    disk_usage=0,
                )
            )
            assignment = self.assignment_repo.create_or_replace(
                "service-123", node_id, "ASSIGNED"
            )
            self.desired_repo.put_next(
                "service-123", "RUNNING", {"web_server": "nginx"}
            )

        service = MasterReconciliationService(lambda: Session(self.engine))
        result = service.report_actual_state(
            "service-123",
            assignment.id,
            1,
            "RUNNING",
            {"web_server": "nginx"},
            {"ready": True},
            "2026-01-01T00:10:00Z",
        )
        state = service.get_state("service-123")

        self.assertTrue(result.accepted)
        self.assertEqual(state.desired.version, 1)
        self.assertEqual(state.actual.status, "RUNNING")
        self.assertEqual(state.assignment.id, assignment.id)

        stale = service.report_actual_state(
            "service-123",
            assignment.id,
            1,
            "PROVISIONING",
            {},
            {},
            "2026-01-01T00:09:00Z",
        )
        self.assertFalse(stale.accepted)


if __name__ == "__main__":
    unittest.main()
