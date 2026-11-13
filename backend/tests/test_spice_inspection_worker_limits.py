"""Tests for SPICE worker resource-limit ordering and failure behavior."""

import builtins
import sys
from types import SimpleNamespace

import pytest

from app.ephemeris import inspect_worker


def test_process_limits_are_installed_before_native_spice_import(tmp_path, monkeypatch, capsys):
    order = []
    fake_spice = SimpleNamespace(
        getfat=lambda _path: ("KPL", "LSK"),
    )
    real_import = builtins.__import__

    def tracked_import(name, *args, **kwargs):
        if name == "spiceypy":
            order.append("spiceypy-import")
            return fake_spice
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(inspect_worker, "apply_process_limits", lambda: order.append("limits"))
    monkeypatch.setattr(builtins, "__import__", tracked_import)
    monkeypatch.setattr(sys, "argv", ["inspect_worker.py", str(tmp_path), "LSK"])

    assert inspect_worker.main() == 0
    assert order == ["limits", "spiceypy-import"]
    assert '"detected_kernel_type":"LSK"' in capsys.readouterr().out


def test_posix_resource_limit_failure_is_not_silently_ignored(monkeypatch):
    calls = []

    def fail_on_limit(limit, values):
        calls.append((limit, values))
        raise OSError("resource limit denied")

    fake_resource = SimpleNamespace(
        RLIMIT_CPU=1,
        RLIMIT_AS=2,
        RLIMIT_FSIZE=3,
        RLIMIT_NOFILE=4,
        RLIMIT_CORE=5,
        setrlimit=fail_on_limit,
    )
    monkeypatch.setitem(sys.modules, "resource", fake_resource)

    with pytest.raises(OSError, match="resource limit denied"):
        inspect_worker.apply_process_limits()

    assert calls == [(fake_resource.RLIMIT_CPU, (8, 8))]
