"""Regression tests for bounded SPICE binary-index metadata extraction."""

from pathlib import Path

import pytest

from app.ephemeris import inspect_worker


def test_spk_coverage_intervals_are_capped_and_report_truncation(monkeypatch):
    monkeypatch.setattr(inspect_worker.spice, "getfat", lambda _path: ("DAF", "SPK"))
    monkeypatch.setattr(inspect_worker.spice, "cell_int", lambda _size: [])
    monkeypatch.setattr(inspect_worker.spice, "cell_double", lambda _size: [])
    monkeypatch.setattr(inspect_worker.spice, "spkobj", lambda _path, _cell: [399])
    monkeypatch.setattr(inspect_worker.spice, "spkcov", lambda *_args: object())
    monkeypatch.setattr(inspect_worker.spice, "wncard", lambda _coverage: 129)
    monkeypatch.setattr(
        inspect_worker.spice,
        "wnfetd",
        lambda _coverage, index: (float(index), float(index + 1)),
    )

    result = inspect_worker.inspect_kernel(Path("synthetic.bsp"), "SPK")

    assert result["object_ids"] == [399]
    assert len(result["coverage_intervals"][0]["intervals"]) == 128
    assert result["coverage_intervals"][0]["truncated"] is True
    assert result["metadata_truncated"] is True


def test_dsk_object_inventory_is_capped_and_reports_truncation(monkeypatch):
    object_ids = list(range(300))
    monkeypatch.setattr(inspect_worker.spice, "getfat", lambda _path: ("DAF", "DSK"))
    monkeypatch.setattr(inspect_worker.spice, "dskobj", lambda _path: object_ids)

    result = inspect_worker.inspect_kernel(Path("synthetic.bds"), "DSK")

    assert result["object_ids"] == object_ids[:256]
    assert len(result["object_ids"]) == 256
    assert result["metadata_truncated"] is True


def test_binary_pck_frame_inventory_is_capped_and_reports_truncation(monkeypatch):
    frame_ids = list(range(300))

    def populate_frames(_path, cell):
        cell.extend(frame_ids)

    monkeypatch.setattr(inspect_worker.spice, "getfat", lambda _path: ("DAF", "PCK"))
    monkeypatch.setattr(inspect_worker.spice, "cell_int", lambda _size: [])
    monkeypatch.setattr(inspect_worker.spice, "pckfrm", populate_frames)

    result = inspect_worker.inspect_kernel(Path("synthetic.bpc"), "PCK")

    assert result["frame_class_ids"] == frame_ids[:256]
    assert len(result["frame_class_ids"]) == 256
    assert result["metadata_truncated"] is True


def test_worker_rejects_registered_type_mismatch_before_index_parsing(monkeypatch):
    monkeypatch.setattr(inspect_worker.spice, "getfat", lambda _path: ("DAF", "SPK"))
    monkeypatch.setattr(
        inspect_worker.spice,
        "spkobj",
        lambda *_args: pytest.fail("index parser must not run after type mismatch"),
    )

    with pytest.raises(ValueError, match="does not match detected type"):
        inspect_worker.inspect_kernel(Path("synthetic.bsp"), "DSK")
