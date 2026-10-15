import json
import os
import socket
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from agents.web_service.adapter import AdapterError, NginxRuntime, create_server


class NginxRuntimeTests(unittest.TestCase):
    def test_apply_observe_remove_are_service_scoped(self):
        commands: list[tuple[str, ...]] = []
        with tempfile.TemporaryDirectory() as directory:
            nginx_pid = Path(directory) / "nginx.pid"
            nginx_pid.write_text(str(os.getpid()), encoding="utf-8")
            runtime = NginxRuntime(
                config_dir=directory,
                nginx_config="/etc/nginx/nginx.conf",
                nginx_pid=nginx_pid,
                run_command=lambda command: commands.append(command),
            )

            applied = runtime.apply("site-a", 1, "server { listen 80; }")
            runtime.apply("site-b", 1, "server { listen 81; }")
            removed = runtime.remove("site-a")

            self.assertEqual(applied["status"], "RUNNING")
            self.assertEqual(removed["status"], "ABSENT")
            self.assertTrue(removed["removed"])
            self.assertEqual(runtime.observe("site-b")["status"], "RUNNING")
            self.assertTrue((Path(directory) / "service-site-b.conf").exists())
            self.assertEqual(len(commands), 10)

    def test_rejects_service_path_traversal(self):
        runtime = NginxRuntime()

        with self.assertRaises(AdapterError) as error:
            runtime.observe("../outside")

        self.assertEqual(error.exception.code, "INVALID_SERVICE_ID")

    def test_unix_socket_http_contract_applies_observes_and_removes(self):
        with tempfile.TemporaryDirectory() as directory:
            socket_path = Path(directory) / "adapter.sock"
            nginx_pid = Path(directory) / "nginx.pid"
            nginx_pid.write_text(str(os.getpid()), encoding="utf-8")
            runtime = NginxRuntime(
                config_dir=Path(directory) / "services",
                nginx_pid=nginx_pid,
                run_command=lambda command: None,
            )
            server = create_server(runtime, socket_path)
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.start()

            def post(
                path: str, payload: dict[str, object]
            ) -> tuple[int, dict[str, object]]:
                body = json.dumps(payload).encode()
                request = (
                    f"POST {path} HTTP/1.0\r\n"
                    f"Host: localhost\r\nContent-Length: {len(body)}\r\n"
                    "Content-Type: application/json\r\n\r\n"
                ).encode() + body
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.connect(str(socket_path))
                    client.sendall(request)
                    response = b""
                    while chunk := client.recv(4096):
                        response += chunk
                header, response_body = response.split(b"\r\n\r\n", 1)
                status = int(header.split(b" ")[1])
                return status, json.loads(response_body)

            try:
                apply_status, applied = post(
                    "/v1/apply",
                    {
                        "service_id": "site-a",
                        "version": 1,
                        "configuration": "server { listen 80; }",
                    },
                )
                observe_status, observed = post("/v1/observe", {"service_id": "site-a"})
                remove_status, removed = post("/v1/remove", {"service_id": "site-a"})
            finally:
                server.shutdown()
                server.server_close()
                server_thread.join()

            self.assertEqual(apply_status, 200)
            self.assertEqual(applied["state"]["status"], "RUNNING")
            self.assertEqual(observe_status, 200)
            self.assertEqual(
                observed["state"]["configuration"], "server { listen 80; }"
            )
            self.assertEqual(remove_status, 200)
            self.assertEqual(removed["state"]["status"], "ABSENT")

    def test_health_fails_when_nginx_process_has_stopped(self):
        with tempfile.TemporaryDirectory() as directory:
            socket_path = Path(directory) / "adapter.sock"
            nginx_pid = Path(directory) / "nginx.pid"
            nginx_pid.write_text(str(os.getpid()), encoding="utf-8")
            server = create_server(
                NginxRuntime(
                    config_dir=Path(directory) / "services",
                    nginx_pid=nginx_pid,
                    run_command=lambda command: None,
                ),
                socket_path,
            )
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.start()

            def health_response() -> tuple[int, dict[str, bool]]:
                request = b"GET /health HTTP/1.0\r\nHost: localhost\r\n\r\n"
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.connect(str(socket_path))
                    client.sendall(request)
                    response = b""
                    while chunk := client.recv(4096):
                        response += chunk
                header, response_body = response.split(b"\r\n\r\n", 1)
                return int(header.split(b" ")[1]), json.loads(response_body)

            try:
                healthy_status, healthy_body = health_response()
                with mock.patch(
                    "agents.web_service.adapter.os.kill",
                    side_effect=ProcessLookupError,
                ):
                    stopped_status, stopped_body = health_response()
            finally:
                server.shutdown()
                server.server_close()
                server_thread.join()

            self.assertEqual(healthy_status, 200)
            self.assertTrue(healthy_body["ready"])
            self.assertEqual(stopped_status, 503)
            self.assertFalse(stopped_body["ready"])


if __name__ == "__main__":
    unittest.main()
