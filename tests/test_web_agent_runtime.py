from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from agents.web_agent.runtime import NginxRuntimeService, create_runtime_app


def test_runtime_app_publishes_and_reports_service_status(tmp_path: Path):
    runtime = NginxRuntimeService(
        config_dir=tmp_path,
        nginx_config_path=tmp_path / "nginx.conf",
        run_command=lambda command: type(
            "Result", (), {"returncode": 0, "stdout": "", "stderr": ""}
        )(),
    )
    app = create_runtime_app(service=runtime)
    client = TestClient(app)

    response = client.put(
        "/v1/services/service-1/config",
        json={
            "desired_version": "v42",
            "lifecycle": "STARTED",
            "configuration": {
                "hostname": "example.test",
                "document_root": "/srv/www/example",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "APPLIED"
    assert payload["desired_version"] == "v42"
    assert (tmp_path / "nginx-service-1.conf").exists()

    status_response = client.get("/v1/services/service-1/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "RUNNING"


def test_runtime_app_rejects_invalid_service_configuration(tmp_path: Path):
    runtime = NginxRuntimeService(
        config_dir=tmp_path,
        nginx_config_path=tmp_path / "nginx.conf",
        run_command=lambda command: type(
            "Result", (), {"returncode": 0, "stdout": "", "stderr": ""}
        )(),
    )
    app = create_runtime_app(service=runtime)
    client = TestClient(app)

    response = client.post(
        "/v1/services/service-1/validate",
        json={"configuration": {"hostname": "example.test"}},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_CONFIGURATION"
