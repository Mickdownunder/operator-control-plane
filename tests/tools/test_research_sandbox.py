import subprocess
from unittest.mock import patch, MagicMock

import pytest

from tools.research_sandbox import run_in_sandbox


def _docker_available() -> bool:
    try:
        completed = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
    except Exception:
        return False
    return completed.returncode == 0


def test_sandbox_success():
    if not _docker_available():
        pytest.skip("docker daemon is not available")
    code = "print('success')"
    res = run_in_sandbox(code, timeout_seconds=5)
    assert res.exit_code == 0
    assert "success" in res.stdout
    assert not res.timeout

def test_sandbox_syntax_error():
    if not _docker_available():
        pytest.skip("docker daemon is not available")
    code = "print('missing quote)"
    res = run_in_sandbox(code, timeout_seconds=5)
    assert res.exit_code != 0
    assert "SyntaxError" in res.stderr

def test_sandbox_timeout():
    if not _docker_available():
        pytest.skip("docker daemon is not available")
    code = "import time\nwhile True: time.sleep(1)"
    res = run_in_sandbox(code, timeout_seconds=2)
    assert res.exit_code != 0
    assert res.timeout
    assert "Sandbox Timeout Exceeded" in res.stderr

def test_sandbox_no_network():
    if not _docker_available():
        pytest.skip("docker daemon is not available")
    code = "import urllib.request\nurllib.request.urlopen('http://google.com')"
    res = run_in_sandbox(code, timeout_seconds=5)
    assert res.exit_code != 0
    assert "URLError" in res.stderr or "NameResolutionError" in res.stderr or "Temporary failure in name resolution" in res.stderr

def test_sandbox_memory_limit():
    """Memory exhaustion should surface as a sandbox failure."""
    oom = MagicMock(returncode=137, stdout="", stderr="")
    with patch("tools.research_sandbox.subprocess.run", return_value=oom):
        res = run_in_sandbox("a = bytearray(1024 * 1024 * 1000)", timeout_seconds=5)
    assert res.exit_code != 0
    assert "MemoryError" in res.stderr or res.exit_code == 137


def test_sandbox_image_fallback_when_primary_missing():
    """When primary image fails with 'no such image', fallback to python:3.11-slim."""
    first = MagicMock(returncode=1, stderr="Error: no such image: operator-research-sandbox:latest", stdout="")
    second = MagicMock(returncode=0, stdout="fallback ok", stderr="")
    with patch("tools.research_sandbox.subprocess.run", side_effect=[first, second]):
        res = run_in_sandbox("print('x')", timeout_seconds=5)
    assert res.exit_code == 0
    assert "fallback ok" in res.stdout


def test_sandbox_timeout_expired_returns_result():
    """subprocess.TimeoutExpired: SandboxResult with timeout=True, exit_code=124."""
    with patch("tools.research_sandbox.subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 2, b"", b"")):
        res = run_in_sandbox("print('x')", timeout_seconds=2)
    assert res.timeout is True
    assert res.exit_code == 124
    assert "Timeout Exceeded" in res.stderr


def test_sandbox_generic_exception_returns_internal_error():
    """Any other exception (e.g. docker not found): exit_code=1, stderr has Internal Error."""
    with patch("tools.research_sandbox.subprocess.run", side_effect=RuntimeError("docker not found")):
        res = run_in_sandbox("print('x')", timeout_seconds=5)
    assert res.exit_code == 1
    assert res.timeout is False
    assert "Internal Error" in res.stderr
