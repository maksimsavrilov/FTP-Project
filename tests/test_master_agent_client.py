import json
import unittest
from urllib.error import URLError

from master.agent_client import WebAgentClient, WebAgentUnavailable


class Response:
    def __init__(self, body):
        self.body = body

    def getcode(self):
        return 202

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class WebAgentClientTests(unittest.TestCase):
    def test_sends_desired_state_to_selected_agent_with_request_id(self):
        captured = {}

        def opener(request, timeout):
            captured["url"] = request.full_url
            captured["method"] = request.method
            captured["headers"] = dict(request.header_items())
            captured["body"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return Response(
                b'{"accepted": true, "service_id": "service-1", "version": 4}'
            )

        client = WebAgentClient(
            "http://fallback-agent.example.test:8002/",
            "master-agent-token",
            opener=opener,
        )

        result = client.send_desired_state(
            "service-1",
            "assignment-2",
            4,
            "RUNNING",
            {"hostname": "example.test", "document_root": "/srv/www/example"},
            request_id="req-dispatch",
            agent_url="http://web-agent.example.test:8002/",
        )

        self.assertEqual(result["accepted"], True)
        self.assertEqual(
            captured["url"],
            "http://web-agent.example.test:8002/v1/services/service-1/desired-state",
        )
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(
            captured["headers"]["Authorization"], "Bearer master-agent-token"
        )
        self.assertEqual(captured["headers"]["X-request-id"], "req-dispatch")
        self.assertEqual(
            captured["body"],
            {
                "service_type": "WEB",
                "assignment_id": "assignment-2",
                "version": 4,
                "lifecycle_state": "RUNNING",
                "configuration": {
                    "hostname": "example.test",
                    "document_root": "/srv/www/example",
                },
            },
        )
        self.assertEqual(captured["timeout"], 5.0)

    def test_reports_unavailable_agent_after_transport_retries(self):
        calls = []

        def opener(request, timeout):
            calls.append(request)
            raise URLError("connection refused")

        client = WebAgentClient(
            "http://web-agent.example.test:8002",
            "master-agent-token",
            max_retries=1,
            opener=opener,
            sleeper=lambda delay: None,
        )

        with self.assertRaises(WebAgentUnavailable):
            client.send_desired_state(
                "service-1", "assignment-2", 4, "RUNNING", {}, "req-dispatch"
            )

        self.assertEqual(len(calls), 2)
