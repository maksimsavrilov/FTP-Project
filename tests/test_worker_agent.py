import json
import unittest

from ftp_project.worker_agent import WorkerAgentMasterClient


class Response:
    def __init__(self, body=b'{"accepted": true}'):
        self.body = body
        self.headers = {}

    def getcode(self):
        return 200

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class WorkerAgentMasterClientTests(unittest.TestCase):
    def test_heartbeats_node_with_agent_credentials(self):
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["method"] = request.method
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return Response(body=b'{"id": "node-1", "status": "ONLINE"}')

        client = WorkerAgentMasterClient(
            "agent-token", base_url="http://master", opener=opener
        )

        result = client.heartbeat(
            "node-1",
            "DEGRADED",
            {"cpu": 2, "memory": 3500, "disk": 5000},
            "2026-01-01T00:10:00Z",
            request_id="req-heartbeat",
        )

        self.assertEqual(result, {"id": "node-1", "status": "ONLINE"})
        self.assertEqual(captured["url"], "http://master/v1/nodes/node-1/heartbeat")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer agent-token")
        self.assertEqual(captured["headers"]["X-request-id"], "req-heartbeat")
        self.assertEqual(captured["body"]["status"], "DEGRADED")
        self.assertEqual(captured["body"]["usage"]["memory"], 3500)
        self.assertEqual(captured["timeout"], 5)

    def test_reports_web_service_actual_state_with_agent_credentials(self):
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["method"] = request.method
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return Response()

        client = WorkerAgentMasterClient(
            "agent-token", base_url="http://master", opener=opener
        )

        result = client.report_web_service_actual_state(
            "service-1",
            "assignment-1",
            2,
            "RUNNING",
            {"web_server": "nginx"},
            {"ready": True},
            "2026-01-01T00:10:00Z",
            request_id="req-agent",
        )

        self.assertEqual(result, {"accepted": True})
        self.assertEqual(captured["url"], "http://master/v1/services/service-1/actual-state")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer agent-token")
        self.assertEqual(captured["headers"]["X-request-id"], "req-agent")
        self.assertEqual(captured["body"]["assignment_id"], "assignment-1")
        self.assertEqual(captured["body"]["version"], 2)
        self.assertEqual(captured["timeout"], 5)
