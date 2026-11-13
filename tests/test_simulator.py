from unittest.mock import Mock, patch

import pytest

from backend.battery_simulator import (
    BatteryFleetSimulator,
    BatteryTelemetrySimulator,
)


class FakeMqttPublisher:
    def __init__(self):
        self.payloads = []
        self.closed = False

    def publish(self, payload):
        self.payloads.append(payload)

    def close(self):
        self.closed = True


def make_simulator(device_id="battery_pack_01", publisher=None):
    return BatteryTelemetrySimulator(
        api_url="http://localhost:5000/",
        mqtt_broker="unused",
        mqtt_port=1883,
        mqtt_topic="unused",
        device_id=device_id,
        mqtt_publisher=publisher or FakeMqttPublisher(),
    )


def test_generated_telemetry_has_valid_shape_and_ranges():
    simulator = make_simulator()

    payload = simulator._generate_telemetry()

    assert payload["device_id"] == "battery_pack_01"
    assert payload["soc"] == round(simulator.soc, 2)
    assert 0 <= payload["soc"] <= 100
    assert -20 <= payload["pack_current"] <= 40
    assert 25 <= payload["temperature"] <= 45
    assert len(payload["cell_voltages"]) == 16
    assert all(3.4 <= voltage <= 3.7 for voltage in payload["cell_voltages"])
    assert payload["pack_voltage"] == round(sum(payload["cell_voltages"]), 2)
    assert -90 <= payload["latitude"] <= 90
    assert -180 <= payload["longitude"] <= 180
    assert payload["health"] in {"GOOD", "WARNING", "CRITICAL"}


def test_simulator_output_is_repeatable_for_same_device():
    first = make_simulator()._generate_telemetry()
    second = make_simulator()._generate_telemetry()

    first.pop("timestamp")
    second.pop("timestamp")
    assert first == second


@pytest.mark.parametrize(
    ("voltage", "temperature", "cells", "expected"),
    [
        (58.01, 30, [3.5] * 16, ["PACK_OVER_VOLTAGE"]),
        (43.99, 30, [3.5] * 16, ["PACK_UNDER_VOLTAGE"]),
        (52, 45.01, [3.5] * 16, ["OVER_TEMPERATURE"]),
        (52, 30, [3.4] + [3.51] * 15, ["CELL_IMBALANCE"]),
        (52, 45, [3.4] + [3.5] * 15, []),
    ],
)
def test_alarm_detection_thresholds(voltage, temperature, cells, expected):
    assert (
        BatteryTelemetrySimulator._detect_alarms(voltage, temperature, cells)
        == expected
    )


def test_push_once_publishes_to_mqtt_and_posts_to_api():
    publisher = FakeMqttPublisher()
    simulator = make_simulator(publisher=publisher)

    with patch("backend.battery_simulator.requests.post") as post:
        payload = simulator.push_once()

    assert publisher.payloads == [payload]
    post.assert_called_once_with(
        "http://localhost:5000/api/telemetry", json=payload, timeout=10
    )


def test_fleet_enforces_minimum_and_builds_device_ids():
    publisher = Mock()
    with patch("backend.battery_simulator.MqttPublisher", return_value=publisher):
        fleet = BatteryFleetSimulator(
            api_url="http://localhost:5000",
            mqtt_broker="unused",
            mqtt_port=1883,
            mqtt_topic="unused",
            battery_count=2,
        )

    assert fleet.battery_count == 10
    assert [sim.device_id for sim in fleet.simulators] == [
        f"battery_pack_{index:02d}" for index in range(1, 11)
    ]
    assert all(sim.mqtt is publisher for sim in fleet.simulators)


def test_fleet_pushes_each_battery_once():
    publisher = Mock()
    with patch("backend.battery_simulator.MqttPublisher", return_value=publisher):
        fleet = BatteryFleetSimulator(
            api_url="http://localhost:5000",
            mqtt_broker="unused",
            mqtt_port=1883,
            mqtt_topic="unused",
            battery_count=10,
        )
    with patch("backend.battery_simulator.requests.post"):
        payloads = fleet.push_once()

    assert len(payloads) == 10
    assert {payload["device_id"] for payload in payloads} == {
        f"battery_pack_{index:02d}" for index in range(1, 11)
    }
