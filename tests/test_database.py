import os
from uuid import uuid4

import pytest

from backend.database import Database


def _telemetry(device_id, timestamp, voltage):
    return {
        "device_id": device_id,
        "timestamp": timestamp,
        "pack_voltage": voltage,
        "pack_current": 12.5,
        "soc": 80.0,
        "temperature": 30.0,
        "cycle_count": 2,
        "latitude": None,
        "longitude": None,
        "cell_voltages": [3.45] * 16,
        "alarms": [],
    }


def test_insert_and_fetch_latest(database):
    first_id = database.insert_telemetry(
        _telemetry("battery_pack_01", "2026-04-07T12:00:00+00:00", 52.0)
    )
    database.insert_telemetry(
        _telemetry("battery_pack_01", "2026-04-07T12:00:05+00:00", 53.0)
    )

    latest = database.fetch_latest()
    assert latest["id"] > first_id
    assert latest["pack_voltage"] == 53.0
    assert latest["cell_voltages"] == [3.45] * 16
    assert database.fetch_latest("battery_pack_02") is None


def test_fetch_history_filters_device_and_limit(database):
    for index in range(3):
        database.insert_telemetry(
            _telemetry(
                "battery_pack_01",
                f"2026-04-07T12:00:0{index}+00:00",
                52.0 + index,
            )
        )
    database.insert_telemetry(
        _telemetry("battery_pack_02", "2026-04-07T12:00:03+00:00", 54.0)
    )

    history = database.fetch_history(limit=2, device_id="battery_pack_01")

    assert [row["pack_voltage"] for row in history] == [54.0, 53.0]


def test_fetch_latest_by_device_returns_latest_row_per_device(database):
    database.insert_telemetry(
        _telemetry("battery_pack_02", "2026-04-07T12:00:00+00:00", 51.0)
    )
    database.insert_telemetry(
        _telemetry("battery_pack_01", "2026-04-07T12:00:01+00:00", 52.0)
    )
    database.insert_telemetry(
        _telemetry("battery_pack_02", "2026-04-07T12:00:02+00:00", 53.0)
    )

    latest = database.fetch_latest_by_device()

    assert [(row["device_id"], row["pack_voltage"]) for row in latest] == [
        ("battery_pack_01", 52.0),
        ("battery_pack_02", 53.0),
    ]


def test_fetch_by_time_range_uses_exclusive_end(database):
    for timestamp in (
        "2026-04-07T12:00:00+00:00",
        "2026-04-07T12:00:01+00:00",
        "2026-04-07T12:00:02+00:00",
    ):
        database.insert_telemetry(_telemetry("battery_pack_01", timestamp, 52.0))

    records = database.fetch_by_time_range(
        "2026-04-07T12:00:00+00:00",
        "2026-04-07T12:00:02+00:00",
        device_id="battery_pack_01",
    )

    assert [row["timestamp"] for row in records] == [
        "2026-04-07T12:00:00+00:00",
        "2026-04-07T12:00:01+00:00",
    ]


def test_database_accepts_legacy_sqlite_path(tmp_path):
    database = Database(str(tmp_path / "voltwatch.db"))
    try:
        database.insert_telemetry(
            _telemetry("battery_pack_01", "2026-04-07T12:00:00+00:00", 52.0)
        )
        assert database.fetch_latest("battery_pack_01")["pack_voltage"] == 52.0
    finally:
        database.close()


def test_postgresql_round_trip():
    database_url = os.getenv("POSTGRES_TEST_URL")
    if not database_url:
        pytest.skip("Set POSTGRES_TEST_URL to run PostgreSQL integration test")

    database = Database(database_url)
    device_id = f"pytest_{uuid4().hex}"
    try:
        database.insert_telemetry(
            _telemetry(device_id, "2026-04-07T12:00:00+00:00", 52.0)
        )
        latest = database.fetch_latest(device_id)
        assert latest["device_id"] == device_id
        assert latest["pack_voltage"] == 52.0
    finally:
        database.close()
