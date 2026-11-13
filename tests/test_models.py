import pytest

from backend.models import TelemetryPayload, compute_health


def _telemetry(**overrides):
    data = {
        "device_id": "battery_pack_01",
        "timestamp": "2026-04-07T12:00:00+00:00",
        "pack_voltage": 52.38,
        "pack_current": 12.6,
        "soc": 91.4,
        "temperature": 33.2,
        "cycle_count": 4,
        "cell_voltages": [3.45] * 16,
        "alarms": [],
    }
    data.update(overrides)
    return data


def test_payload_converts_values_and_preserves_optional_location():
    payload = TelemetryPayload.from_dict(
        _telemetry(
            pack_voltage="52.38",
            soc="91.4",
            cell_voltages=["3.45"] * 16,
            latitude="-28.15",
            longitude="29.53",
        )
    )

    assert payload.device_id == "battery_pack_01"
    assert payload.pack_voltage == 52.38
    assert payload.soc == 91.4
    assert payload.cell_voltages == [3.45] * 16
    assert payload.latitude == -28.15
    assert payload.longitude == 29.53
    assert TelemetryPayload.from_dict(_telemetry()).latitude is None
    assert payload.to_dict()["alarms"] == []


def test_payload_rejects_missing_required_field():
    data = _telemetry()
    del data["temperature"]

    with pytest.raises(ValueError, match="Missing telemetry fields: temperature"):
        TelemetryPayload.from_dict(data)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"timestamp": "not-a-timestamp"}, "Invalid isoformat string"),
        ({"soc": 100.1}, "soc must be within 0-100"),
        ({"cell_voltages": [3.45] * 15}, "cell_voltages must contain 16 values"),
        ({"latitude": 90.1}, "latitude must be within -90 to 90"),
        ({"longitude": -180.1}, "longitude must be within -180 to 180"),
    ],
)
def test_payload_rejects_invalid_values(overrides, message):
    with pytest.raises(ValueError, match=message):
        TelemetryPayload.from_dict(_telemetry(**overrides))


def test_compute_health_applies_health_thresholds():
    good = {
        "temperature": 40,
        "pack_voltage": 44,
        "cell_voltages": [3.45] * 16,
    }

    assert compute_health(None) == "UNKNOWN"
    assert compute_health(good) == "GOOD"
    assert compute_health({**good, "temperature": 40.1}) == "WARNING"
    assert compute_health({**good, "cell_voltages": [3.4] + [3.48] * 15}) == "GOOD"
    assert compute_health({**good, "cell_voltages": [3.4] + [3.49] * 15}) == "WARNING"
    assert compute_health({**good, "pack_voltage": 43.99}) == "CRITICAL"
    assert compute_health({**good, "pack_voltage": 58.01}) == "CRITICAL"
