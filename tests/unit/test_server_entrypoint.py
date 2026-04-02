from __future__ import annotations

from pathlib import Path

import pytest

from tlvflow.api import app as app_module
from tlvflow.api import server


def test_run_uses_cloud_run_port_and_host(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(target: str, *, host: str, port: int) -> None:
        captured["target"] = target
        captured["host"] = host
        captured["port"] = port

    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setattr(server.uvicorn, "run", fake_run)

    server.run()

    assert captured["target"] == "tlvflow.api.app:app"
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9090


def test_resolve_data_dir_relative_to_cwd(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    sandbox = tmp_path / "workspace"
    sandbox.mkdir()
    monkeypatch.chdir(sandbox)
    monkeypatch.setenv("TLVFLOW_DATA_DIR", "data")

    assert app_module._resolve_data_dir() == sandbox / "data"


def test_resolve_data_dir_rejects_parent_escape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    sandbox = tmp_path / "workspace"
    nested = sandbox / "nested"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    monkeypatch.setenv("TLVFLOW_DATA_DIR", "../outside")

    with pytest.raises(ValueError):
        app_module._resolve_data_dir()
