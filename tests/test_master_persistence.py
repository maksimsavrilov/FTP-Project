import unittest
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from master.persistence.models import Base, WorkerNode, ServiceAssignment, DesiredState, ActualState
from master.persistence.repositories import (
    WorkerNodeRepository,
    ServiceAssignmentRepository,
    DesiredStateRepository,
    ActualStateRepository,
)


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
        self.assertEqual(updated.status, "DEGRADED")

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


if __name__ == "__main__":
    unittest.main()
