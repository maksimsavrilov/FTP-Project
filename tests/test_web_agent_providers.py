import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any

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

    def apply(self, configuration: str, *, service_id: str | None = None) -> ProviderApplyResult:
        self.calls.append(("apply", configuration, service_id))
        if self.error:
            raise self.error
        return ProviderApplyResult(status="RUNNING", health={"ready": True})

    def remove_service(self, service_id: str) -> ProviderApplyResult:
        self.calls.append(("remove_service", service_id))
        if self.error:
            raise self.error
        return ProviderApplyResult(status="REMOVED", health={"ready": True, "service_id": service_id})

    def inspect(self, service_id: str | None = None) -> dict[str, Any]:
        self.calls.append(("inspect", service_id))
        return {"provider": self.name, "service_id": service_id}


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
            nginx_config_path="/etc/nginx/nginx.conf",
            write_configuration=lambda path, content: written.append((path, content)),
            run_command=lambda command: commands.append(tuple(command)),
        )

        result = provider.apply("server {}")

        self.assertEqual(result.status, "RUNNING")
        self.assertEqual(written, [(Path("/tmp/web.conf"), "server {}")])
        self.assertEqual(commands, [
            ("nginx", "-t", "-c", "/etc/nginx/nginx.conf"),
            ("systemctl", "reload", "nginx"),
        ])

    def test_nginx_inspect_reports_runtime_readiness(self):
        commands: list[tuple[str, ...]] = []
        provider = NginxProvider(
            config_path="/tmp/web.conf",
            nginx_config_path="/etc/nginx/nginx.conf",
            run_command=lambda command: commands.append(tuple(command)),
        )

        self.assertEqual(
            provider.inspect("service-9"),
            {
                "provider": "nginx",
                "ready": True,
                "service_id": "service-9",
                "config_path": "/tmp/web-service-9.conf",
            },
        )
        self.assertEqual(commands, [("nginx", "-t", "-c", "/etc/nginx/nginx.conf")])

    def test_nginx_reloads_only_after_validation_success(self):
        commands: list[tuple[str, ...]] = []

        def run_command(command: tuple[str, ...]) -> None:
            commands.append(command)
            if command[:3] == ("nginx", "-t", "-c"):
                raise ProviderExecutionError("nginx validation failed")

        provider = NginxProvider(
            config_path="/tmp/web.conf",
            nginx_config_path="/etc/nginx/nginx.conf",
            write_configuration=lambda path, content: None,
            run_command=run_command,
        )

        with self.assertRaises(ProviderExecutionError):
            provider.apply("server {}")

        self.assertEqual(commands, [("nginx", "-t", "-c", "/etc/nginx/nginx.conf")])

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

    def test_nginx_service_files_are_scoped_per_service_and_removal_is_idempotent(self):
        writes: list[tuple[Path, str]] = []
        commands: list[tuple[str, ...]] = []
        def write_configuration(path: Path, content: str) -> None:
            writes.append((path, content))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        provider = NginxProvider(
            config_path="/tmp/ftp-project/nginx.conf",
            nginx_config_path="/tmp/ftp-project/nginx.conf",
            write_configuration=write_configuration,
            run_command=lambda command: commands.append(tuple(command)),
        )

        provider.apply(provider.generate_configuration(NEUTRAL_STATE), service_id="service-1")
        provider.apply(provider.generate_configuration(NEUTRAL_STATE), service_id="service-2")
        provider.remove_service("service-1")
        provider.remove_service("service-1")

        self.assertEqual(writes[0][0], Path("/tmp/ftp-project/nginx-service-1.conf"))
        self.assertEqual(writes[1][0], Path("/tmp/ftp-project/nginx-service-2.conf"))
        self.assertEqual(commands, [
            ("nginx", "-t", "-c", "/tmp/ftp-project/nginx.conf"),
            ("systemctl", "reload", "nginx"),
            ("nginx", "-t", "-c", "/tmp/ftp-project/nginx.conf"),
            ("systemctl", "reload", "nginx"),
            ("nginx", "-t", "-c", "/tmp/ftp-project/nginx.conf"),
            ("systemctl", "reload", "nginx"),
            ("nginx", "-t", "-c", "/tmp/ftp-project/nginx.conf"),
            ("systemctl", "reload", "nginx"),
        ])
        self.assertFalse(Path("/tmp/ftp-project/nginx-service-1.conf").exists())
        self.assertTrue(Path("/tmp/ftp-project/nginx-service-2.conf").exists())

    def test_reconciliation_removes_service_on_stopped_state(self):
        def write_configuration(path: Path, content: str) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        provider = NginxProvider(
            config_path="/tmp/ftp-project-lifecycle/nginx.conf",
            write_configuration=write_configuration,
            run_command=lambda command: None,
        )
        store = WebAgentDesiredStateStore(provider=provider)
        store.accept("service-stop", DesiredWebServiceState(
            service_type="WEB",
            assignment_id="assignment-1",
            version=1,
            lifecycle_state="RUNNING",
            configuration=NEUTRAL_STATE,
        ))
        store.reconcile("service-stop")

        store.accept("service-stop", DesiredWebServiceState(
            service_type="WEB",
            assignment_id="assignment-1",
            version=2,
            lifecycle_state="STOPPED",
            configuration=NEUTRAL_STATE,
        ))
        first = store.reconcile("service-stop")
        second = store.reconcile("service-stop")

        self.assertEqual(first.status, "STOPPED")
        self.assertEqual(second.status, "STOPPED")
        self.assertFalse(Path("/tmp/ftp-project-lifecycle/nginx-service-stop.conf").exists())

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
