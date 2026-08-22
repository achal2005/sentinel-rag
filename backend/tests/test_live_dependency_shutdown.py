"""Opt-in tests that physically stop Ollama and the Sentinel Postgres service.

These tests intentionally change local service state, so ordinary ``pytest``
runs skip them.  Enable them only on a controlled machine:

    RUN_LIVE_SHUTDOWN_TESTS=1 pytest -q -s \
        backend/tests/test_live_dependency_shutdown.py

Both tests require the dependency to be healthy before the test starts and
restore it in ``finally``.  PostgreSQL data lives in the existing Compose
volume and is checked before and after the shutdown.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from app import db, router
from app.answer import answer
from app.config import LLM_PROVIDER, OLLAMA_HOST
from app.graph import escalate_node


ROOT = Path(__file__).resolve().parents[2]
OPT_IN_ENV = "RUN_LIVE_SHUTDOWN_TESTS"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

pytestmark = pytest.mark.live_shutdown


def _enabled() -> bool:
    return os.environ.get(OPT_IN_ENV, "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


@pytest.fixture(autouse=True)
def _require_explicit_opt_in() -> None:
    if not _enabled():
        pytest.skip(
            f"physical dependency shutdown is opt-in; set {OPT_IN_ENV}=1"
        )


def _run(
    args: list[str],
    *,
    timeout: float = 90,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        check=check,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _run_configured(command: str, *, timeout: float = 90) -> None:
    result = subprocess.run(
        command,
        cwd=ROOT,
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"service command failed ({result.returncode}): {details}")


def _wait_until(predicate, *, expected: bool, timeout: float, label: str) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if bool(predicate()) is expected:
            return
        time.sleep(0.5)
    state = "healthy" if expected else "stopped"
    raise AssertionError(f"{label} did not become {state} within {timeout:.0f}s")


def _ollama_is_healthy() -> bool:
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=2) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def _assert_local_ollama() -> None:
    parsed = urlsplit(OLLAMA_HOST)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in LOCAL_HOSTS:
        pytest.fail(
            "refusing to stop a non-local Ollama endpoint: "
            f"OLLAMA_HOST={OLLAMA_HOST!r}"
        )


def _windows_ollama_executable() -> Path | None:
    local_app_data = os.environ.get("LOCALAPPDATA")
    candidates = []
    if local_app_data:
        install = Path(local_app_data) / "Programs" / "Ollama"
        candidates.extend((install / "Ollama app.exe", install / "ollama.exe"))
    resolved = shutil.which("ollama")
    if resolved:
        candidates.append(Path(resolved))
    return next((candidate for candidate in candidates if candidate.exists()), None)


def _stop_ollama() -> None:
    stop_command = os.environ.get("OLLAMA_STOP_COMMAND")
    start_command = os.environ.get("OLLAMA_START_COMMAND")
    if bool(stop_command) != bool(start_command):
        pytest.fail(
            "set both OLLAMA_STOP_COMMAND and OLLAMA_START_COMMAND, or neither"
        )
    if stop_command:
        _run_configured(stop_command)
        return
    if os.name != "nt":
        pytest.skip(
            "non-Windows live shutdown requires OLLAMA_STOP_COMMAND and "
            "OLLAMA_START_COMMAND"
        )
    script = (
        "$ErrorActionPreference='Stop'; "
        "Get-Process -ErrorAction SilentlyContinue | "
        "Where-Object { $_.ProcessName -in @('ollama app','ollama') } | "
        "Stop-Process -Force"
    )
    _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script])


def _start_ollama() -> None:
    start_command = os.environ.get("OLLAMA_START_COMMAND")
    if start_command:
        _run_configured(start_command)
        return
    executable = _windows_ollama_executable()
    if executable is None:
        raise RuntimeError("could not locate Ollama for service restoration")

    # Prefer the desktop app when installed because it restores the user's
    # original tray-managed server.  The CLI fallback runs ``ollama serve``.
    args = "" if executable.name.lower() == "ollama app.exe" else "serve"
    escaped_path = str(executable).replace("'", "''")
    escaped_args = args.replace("'", "''")
    script = f"Start-Process -FilePath '{escaped_path}' -WindowStyle Hidden"
    if escaped_args:
        script += f" -ArgumentList '{escaped_args}'"
    _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script])


def _db_is_healthy() -> bool:
    try:
        conn = db.connect()
        try:
            return conn.execute("SELECT 1").fetchone()[0] == 1
        finally:
            conn.close()
    except Exception:
        return False


def _chunk_count() -> int:
    conn = db.connect()
    try:
        return int(conn.execute("SELECT count(*) FROM chunks").fetchone()[0])
    finally:
        conn.close()


def _assert_exact_postgres_target() -> None:
    if shutil.which("docker") is None:
        pytest.skip("Docker CLI is required for the live Postgres shutdown test")
    container = _run(["docker", "compose", "ps", "-q", "db"]).stdout.strip()
    if not container:
        pytest.skip("Compose service 'db' must be running before this test")
    name = _run(
        ["docker", "inspect", "--format", "{{.Name}}", container]
    ).stdout.strip()
    if name != "/sentinel-db":
        pytest.fail(f"refusing to stop unexpected database container {name!r}")


def test_real_ollama_shutdown_fails_closed_to_human_escalation() -> None:
    if LLM_PROVIDER != "ollama":
        pytest.skip("Ollama shutdown applies only when LLM_PROVIDER=ollama")
    _assert_local_ollama()
    if not _ollama_is_healthy():
        pytest.skip("Ollama must be healthy before the shutdown test")

    stopped = False
    try:
        _stop_ollama()
        _wait_until(
            _ollama_is_healthy,
            expected=False,
            timeout=20,
            label="Ollama",
        )
        stopped = True

        started = time.monotonic()
        decision = router.route("Meridian analytics capability review request.")
        elapsed = time.monotonic() - started
        outcome = escalate_node({"route": decision.route, "decision": decision})

        assert elapsed < 10, f"Ollama failure took too long: {elapsed:.2f}s"
        assert decision.route == "escalate"
        assert decision.intent == "unclassified"
        assert decision.action_required is False
        assert decision.raw.startswith("router_error:")
        assert outcome["escalated"] is True
        assert outcome["reason"] == "router_escalate"
        assert "human" in outcome["answer"].lower()
    finally:
        if stopped or not _ollama_is_healthy():
            _start_ollama()
            _wait_until(
                _ollama_is_healthy,
                expected=True,
                timeout=60,
                label="Ollama",
            )


def test_real_postgres_shutdown_escalates_fast_and_preserves_data() -> None:
    _assert_exact_postgres_target()
    if not _db_is_healthy():
        pytest.skip("Sentinel Postgres must be healthy before the shutdown test")
    chunks_before = _chunk_count()
    stopped = False

    try:
        _run(["docker", "compose", "stop", "db"])
        _wait_until(
            _db_is_healthy,
            expected=False,
            timeout=20,
            label="Sentinel Postgres",
        )
        stopped = True

        started = time.monotonic()
        outcome = answer("How do I rotate a Meridian secret API key?")
        elapsed = time.monotonic() - started

        assert elapsed < db.DB_CONNECT_TIMEOUT + 2
        assert outcome.escalated is True
        assert outcome.reason == "retrieval_dependency_unavailable"
        assert outcome.citations == []
        assert outcome.hits == []
        assert "can't verify an answer" in outcome.text
    finally:
        if stopped or not _db_is_healthy():
            _run(["docker", "compose", "up", "-d", "--wait", "db"])
            _wait_until(
                _db_is_healthy,
                expected=True,
                timeout=60,
                label="Sentinel Postgres",
            )

    assert _chunk_count() == chunks_before
