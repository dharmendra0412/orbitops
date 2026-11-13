"""Regression tests for bounded SPICE binary-index metadata extraction."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.ephemeris import inspect_worker


def _install_fake_spice(monkeypatch, **functions):
    fake_spice = SimpleNamespace(**functions)
    monkeypatch.setitem(sys.modules, "spiceypy", fake_spice)
    return fake_spice


def test_spk_coverage_intervals_are_capped_and_report_truncation(monkeypatch):
    _install_fake_spice(
        monkeypatch,
        getfat=lambda _path: ("DAF", "SPK"),
        cell_int=lambda _size: [],
        cell_double=lambda _size: [],
        spkobj=lambda _path, _cell: [399],
        spkcov=lambda *_args: object(),
        wncard=lambda _coverage: 129,
        wnfetd=lambda _coverage, index: (float(index), float(index + 1)),
    )

    result = inspect_worker.inspect_kernel(Path("synthetic.bsp"), "SPK")

    assert result["object_ids"] == [399]
    assert len(result["coverage_intervals"][0]["intervals"]) == 128
    assert result["coverage_intervals"][0]["truncated"] is True
    assert result["metadata_truncated"] is True


def test_dsk_object_inventory_is_capped_and_reports_truncation(monkeypatch):
    object_ids = list(range(300))
    _install_fake_spice(
        monkeypatch,
        getfat=lambda _path: ("DAF", "DSK"),
        dskobj=lambda _path: object_ids,
    )

    result = inspect_worker.inspect_kernel(Path("synthetic.bds"), "DSK")

    assert result["object_ids"] == object_ids[:256]
    assert len(result["object_ids"]) == 256
    assert result["metadata_truncated"] is True


def test_binary_pck_frame_inventory_is_capped_and_reports_truncation(monkeypatch):
    frame_ids = list(range(300))

    def populate_frames(_path, cell):
        cell.extend(frame_ids)

    _install_fake_spice(
        monkeypatch,
        getfat=lambda _path: ("DAF", "PCK"),
        cell_int=lambda _size: [],
        pckfrm=populate_frames,
    )

    result = inspect_worker.inspect_kernel(Path("synthetic.bpc"), "PCK")

    assert result["frame_class_ids"] == frame_ids[:256]
    assert len(result["frame_class_ids"]) == 256
    assert result["metadata_truncated"] is True


def test_worker_rejects_registered_type_mismatch_before_index_parsing(monkeypatch):
    _install_fake_spice(
        monkeypatch,
        getfat=lambda _path: ("DAF", "SPK"),
        spkobj=lambda *_args: pytest.fail("index parser must not run after type mismatch"),
    )

    with pytest.raises(ValueError, match="does not match detected type"):
        inspect_worker.inspect_kernel(Path("synthetic.bsp"), "DSK")
