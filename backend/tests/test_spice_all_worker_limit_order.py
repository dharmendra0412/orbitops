"""Regression tests that every SPICE worker applies limits before native imports."""

import builtins
import hashlib
import sys
from types import SimpleNamespace

from app.ephemeris import frame_worker, time_worker


def _track_native_import(monkeypatch, module, fake_spice):
    order = []
    real_import = builtins.__import__

    def tracked_import(name, *args, **kwargs):
        if name == "spiceypy":
            order.append("spiceypy")
            return fake_spice
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(module, "apply_process_limits", lambda: order.append("limits"))
    monkeypatch.setattr(builtins, "__import__", tracked_import)
    return order


def test_time_worker_applies_limits_before_importing_spiceypy(tmp_path, monkeypatch):
    artifact = tmp_path / "kernel.tls"
    artifact.write_bytes(b"synthetic-lsk")
    fake_spice = SimpleNamespace(
        getfat=lambda _path: ("KPL", "LSK"),
        furnsh=lambda _path: None,
        str2et=lambda _value: 12.5,
        et2utc=lambda *_args: "2000-01-01T12:00:00",
        kclear=lambda: None,
    )
    order = _track_native_import(monkeypatch, time_worker, fake_spice)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "time_worker.py",
            str(artifact),
            "utc_to_et",
            "2000-01-01T12:00:00 UTC",
            "6",
            hashlib.sha256(b"synthetic-lsk").hexdigest(),
        ],
    )

    assert time_worker.main() == 0
    assert order == ["limits", "spiceypy"]


def test_frame_worker_applies_limits_before_importing_spiceypy(tmp_path, monkeypatch):
    artifact = tmp_path / "kernel.tf"
    artifact.write_bytes(b"synthetic-fk")
    fake_spice = SimpleNamespace(
        getfat=lambda _path: ("KPL", "FK"),
        furnsh=lambda _path: None,
        namfrm=lambda _name: 0,
        kclear=lambda: None,
    )
    order = _track_native_import(monkeypatch, frame_worker, fake_spice)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "frame_worker.py",
            str(artifact),
            hashlib.sha256(b"synthetic-fk").hexdigest(),
            "UNKNOWN_FROM",
            "UNKNOWN_TO",
            "0.0",
            "position",
            "null",
        ],
    )

    assert frame_worker.main() == 2
    assert order == ["limits", "spiceypy"]
