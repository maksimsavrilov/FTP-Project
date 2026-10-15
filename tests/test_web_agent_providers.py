import os
import tempfile
import threading
import unittest
from collections.abc import Mapping
from typing import Any

from agents.web_agent.app import DesiredWebServiceState, WebAgentDesiredStateStore
from agents.web_agent.providers import (
    NginxProvider,
    ProviderApplyResult,
    ProviderConfigurationError,
    ProviderExecutionError,
)
from agents.web_service.adapter import NginxRuntime, create_server

NEUTRAL_STATE = {
    "hostname": "example.test",
    "document_root": "/srv/www/example",
    "php_version": "8.3",
    "tls": {"enabled": True},
}


class FakeProvider:
    name = "fake"

    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls = []

    def validate(self, desired: Mapping[str, Any]) -> None:
        self.calls.append(("validate", desired))
        if self.error:
            raise self.error

    def generate_configuration(self, desired: Mapping[str, Any]) -> str:
        self.calls.append(("generate", desired))
        return "generated"

    def apply(
        self,
        configuration: str,
        *,
        service_id: str,
        version: int,
    ) -> ProviderApplyResult:
        self.calls.append(("apply", configuration, service_id, version))
        if self.error:
            raise self.error
        return ProviderApplyResult(status="RUNNING", health={"ready": True})

    def remove_service(self, service_id: str) -> ProviderApplyResult:
        self.calls.append(("remove_service", service_id))
        if self.error:
            raise self.error
        return ProviderApplyResult(
            status="REMOVED", health={"ready": True, "service_id": service_id}
        )

    def inspect(self, service_id: str | None = None) -> dict[str, Any]:
        self.calls.append(("inspect", service_id))
        return {
            "provider": self.name,
            "service_id": service_id,
            "status": "RUNNING",
            "configuration": "observed configuration",
        }


class WebProviderTests(unittest.TestCase):
    def test_nginx_generates_configuration_from_neutral_state(self):
        provider = NginxProvider()

        configuration = provider.generate_configuration(NEUTRAL_STATE)

        self.assertIn("server_name example.test;", configuration)
        self.assertIn("root /srv/www/example;", configuration)
        self.assertIn("# PHP runtime: 8.3", configuration)
        self.assertNotIn("worker_processes", configuration)

    def test_nginx_rejects_invalid_configuration(self):
        with self.assertRaises(ProviderConfigurationError):
            NginxProvider().validate({"hostname": "example.test"})

    def test_reconciliation_applies_provider_and_is_idempotent(self):
        provider = FakeProvider()
        store = WebAgentDesiredStateStore(provider=provider)
        state = DesiredWebServiceState(
            service_type="WEB",
            assignment_id="assignment-1",
            version=1,
            lifecycle_state="RUNNING",
            configuration=NEUTRAL_STATE,
        )
        store.accept("service-1", state)

        first = store.reconcile("service-1")
        second = store.reconcile("service-1")

        self.assertEqual(first.status, "RUNNING")
        self.assertEqual(first.observed_status, "RUNNING")
        self.assertEqual(first.observed_configuration, "observed configuration")
        self.assertEqual(second, first)
        self.assertEqual(
            [call[0] for call in provider.calls],
            [
                "validate",
                "generate",
                "apply",
                "inspect",
            ],
        )

    def test_nginx_provider_reconciles_service_scoped_state_over_socket(self):
        with tempfile.TemporaryDirectory() as directory:
            socket_path = os.path.join(directory, "adapter.sock")
            nginx_pid = os.path.join(directory, "nginx.pid")
            with open(nginx_pid, "w", encoding="utf-8") as pid_file:
                pid_file.write(str(os.getpid()))
            server = create_server(
                NginxRuntime(
                    config_dir=os.path.join(directory, "services"),
                    nginx_pid=nginx_pid,
                    run_command=lambda command: None,
                ),
                socket_path,
            )
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.start()
            provider = NginxProvider(socket_path=socket_path)
            try:
                store = WebAgentDesiredStateStore(provider=provider)
                store.accept(
                    "service-1",
                    DesiredWebServiceState(
                        service_type="WEB",
                        assignment_id="assignment-1",
                        version=4,
                        lifecycle_state="RUNNING",
                        configuration=NEUTRAL_STATE,
                    ),
                )
                one = store.reconcile("service-1")
                two = provider.apply(
                    provider.generate_configuration(NEUTRAL_STATE),
                    service_id="service-2",
                    version=2,
                )
                actual_one = one.health["actual"]
                provider.remove_service("service-1")
                actual_removed = provider.inspect("service-1")
                actual_two = provider.inspect("service-2")

                reported: list[tuple[object, ...]] = []

                class MasterReporter:
                    def report_web_service_actual_state(self, *args, **kwargs):
                        reported.append(args)
                        return {"accepted": True}

                store.report_actual_state(
                    "service-1",
                    MasterReporter(),
                    result=one,
                    observed_at="2026-10-15T00:00:00Z",
                )
            finally:
                server.shutdown()
                server.server_close()
                server_thread.join()

        self.assertEqual(one.status, "RUNNING")
        self.assertEqual(one.observed_status, "RUNNING")
        self.assertIn("server_name example.test;", one.observed_configuration)
        self.assertEqual(two.status, "RUNNING")
        self.assertEqual(actual_one["status"], "RUNNING")
        self.assertIn("server_name example.test;", actual_one["configuration"])
        self.assertIn(
            "server_name example.test;", reported[0][4]["nginx"]
        )
        self.assertEqual(reported[0][3], "RUNNING")
        self.assertEqual(actual_removed["status"], "ABSENT")
        self.assertEqual(actual_two["status"], "RUNNING")

    def test_reconciliation_removes_service_on_stopped_state(self):
        with tempfile.TemporaryDirectory() as directory:
            socket_path = os.path.join(directory, "adapter.sock")
            nginx_pid = os.path.join(directory, "nginx.pid")
            with open(nginx_pid, "w", encoding="utf-8") as pid_file:
                pid_file.write(str(os.getpid()))
            server = create_server(
                NginxRuntime(
                    config_dir=os.path.join(directory, "services"),
                    nginx_pid=nginx_pid,
                    run_command=lambda command: None,
                ),
                socket_path,
            )
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.start()
            provider = NginxProvider(socket_path=socket_path)
            store = WebAgentDesiredStateStore(provider=provider)
            try:
                store.accept(
                    "service-stop",
                    DesiredWebServiceState(
                        service_type="WEB",
                        assignment_id="assignment-1",
                        version=1,
                        lifecycle_state="RUNNING",
                        configuration=NEUTRAL_STATE,
                    ),
                )
                store.reconcile("service-stop")

                store.accept(
                    "service-stop",
                    DesiredWebServiceState(
                        service_type="WEB",
                        assignment_id="assignment-1",
                        version=2,
                        lifecycle_state="STOPPED",
                        configuration=NEUTRAL_STATE,
                    ),
                )
                first = store.reconcile("service-stop")
                second = store.reconcile("service-stop")
                actual = provider.inspect("service-stop")
            finally:
                server.shutdown()
                server.server_close()
                server_thread.join()

        self.assertEqual(first.status, "STOPPED")
        self.assertEqual(first.observed_status, "ABSENT")
        self.assertIsNone(first.observed_configuration)
        self.assertEqual(second.status, "STOPPED")
        self.assertEqual(actual["status"], "ABSENT")

    def test_reconciliation_reports_configuration_failure(self):
        provider = FakeProvider(ProviderConfigurationError("invalid web state"))
        store = WebAgentDesiredStateStore(provider=provider)
        store.accept(
            "service-1",
            DesiredWebServiceState(
                service_type="WEB",
                assignment_id="assignment-1",
                version=1,
                lifecycle_state="RUNNING",
                configuration=NEUTRAL_STATE,
            ),
        )

        result = store.reconcile("service-1")

        self.assertEqual(result.status, "ERROR")
        self.assertEqual(result.error_code, "PROVIDER_CONFIGURATION_INVALID")
        self.assertEqual(result.error_message, "invalid web state")

    def test_reconciliation_reports_execution_failure(self):
        provider = FakeProvider(ProviderExecutionError("reload failed"))
        store = WebAgentDesiredStateStore(provider=provider)
        store.accept(
            "service-1",
            DesiredWebServiceState(
                service_type="WEB",
                assignment_id="assignment-1",
                version=1,
                lifecycle_state="RUNNING",
                configuration=NEUTRAL_STATE,
            ),
        )

        result = store.reconcile("service-1")

        self.assertEqual(result.status, "ERROR")
        self.assertEqual(result.error_code, "PROVIDER_EXECUTION_FAILED")
        self.assertEqual(result.error_message, "reload failed")


if __name__ == "__main__":
    unittest.main()
