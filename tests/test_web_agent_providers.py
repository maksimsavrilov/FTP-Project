import unittest
from pathlib import Path
from typing import Any, Mapping

from agents.web_agent.app import DesiredWebServiceState, WebAgentDesiredStateStore
from agents.web_agent.providers import (
    NginxProvider,
    ProviderApplyResult,
    ProviderConfigurationError,
    ProviderExecutionError,
)


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

    def apply(self, configuration: str) -> ProviderApplyResult:
        self.calls.append(("apply", configuration))
        if self.error:
            raise self.error
        return ProviderApplyResult(status="RUNNING", health={"ready": True})

    def inspect(self) -> dict[str, Any]:
        self.calls.append(("inspect",))
        return {"provider": self.name}


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

    def test_nginx_applies_configuration_without_real_nginx(self):
        written: list[tuple[Path, str]] = []
        commands: list[tuple[str, ...]] = []
        provider = NginxProvider(
            config_path="/tmp/web.conf",
            write_configuration=lambda path, content: written.append((path, content)),
            run_command=lambda command: commands.append(tuple(command)),
        )

        result = provider.apply("server {}")

        self.assertEqual(result.status, "RUNNING")
        self.assertEqual(written, [(Path("/tmp/web.conf"), "server {}")])
        self.assertEqual(commands, [
            ("nginx", "-t", "-c", "/tmp/web.conf"),
            ("systemctl", "reload", "nginx"),
        ])

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
        self.assertEqual(second, first)
        self.assertEqual([call[0] for call in provider.calls], [
            "validate", "generate", "apply", "inspect",
        ])

    def test_reconciliation_reports_configuration_failure(self):
        provider = FakeProvider(ProviderConfigurationError("invalid web state"))
        store = WebAgentDesiredStateStore(provider=provider)
        store.accept("service-1", DesiredWebServiceState(
            service_type="WEB",
            assignment_id="assignment-1",
            version=1,
            lifecycle_state="RUNNING",
            configuration=NEUTRAL_STATE,
        ))

        result = store.reconcile("service-1")

        self.assertEqual(result.status, "ERROR")
        self.assertEqual(result.error_code, "PROVIDER_CONFIGURATION_INVALID")
        self.assertEqual(result.error_message, "invalid web state")

    def test_reconciliation_reports_execution_failure(self):
        provider = FakeProvider(ProviderExecutionError("reload failed"))
        store = WebAgentDesiredStateStore(provider=provider)
        store.accept("service-1", DesiredWebServiceState(
            service_type="WEB",
            assignment_id="assignment-1",
            version=1,
            lifecycle_state="RUNNING",
            configuration=NEUTRAL_STATE,
        ))

        result = store.reconcile("service-1")

        self.assertEqual(result.status, "ERROR")
        self.assertEqual(result.error_code, "PROVIDER_EXECUTION_FAILED")
        self.assertEqual(result.error_message, "reload failed")


if __name__ == "__main__":
    unittest.main()
