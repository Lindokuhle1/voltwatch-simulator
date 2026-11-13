import unittest

from backend.models import TelemetryPayload, compute_health


def valid_telemetry(**overrides):
    telemetry = {
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
    telemetry.update(overrides)
    return telemetry


class TelemetryPayloadTests(unittest.TestCase):
    def test_from_dict_converts_values_and_preserves_optional_location(self):
        source = valid_telemetry(
            pack_voltage="52.38",
            soc="91.4",
            cell_voltages=["3.45"] * 16,
            latitude="-28.15",
            longitude="29.53",
        )

        payload = TelemetryPayload.from_dict(source)

        self.assertEqual(payload.device_id, "battery_pack_01")
        self.assertEqual(payload.pack_voltage, 52.38)
        self.assertEqual(payload.soc, 91.4)
        self.assertEqual(payload.cell_voltages, [3.45] * 16)
        self.assertEqual(payload.latitude, -28.15)
        self.assertEqual(payload.longitude, 29.53)
        self.assertIsNone(TelemetryPayload.from_dict(valid_telemetry()).latitude)
        self.assertEqual(payload.to_dict()["alarms"], [])

    def test_from_dict_rejects_missing_required_fields(self):
        telemetry = valid_telemetry()
        del telemetry["temperature"]

        with self.assertRaisesRegex(ValueError, "Missing telemetry fields: temperature"):
            TelemetryPayload.from_dict(telemetry)

    def test_validation_rejects_invalid_timestamp_soc_and_cell_count(self):
        invalid_values = (
            ({"timestamp": "not-a-timestamp"}, "Invalid isoformat string"),
            ({"soc": 100.1}, "soc must be within 0-100"),
            ({"cell_voltages": [3.45] * 15}, "cell_voltages must contain 16 values"),
        )
        for overrides, message in invalid_values:
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValueError, message):
                    TelemetryPayload.from_dict(valid_telemetry(**overrides))

    def test_validation_rejects_out_of_range_coordinates(self):
        for overrides, message in (
            ({"latitude": 90.1}, "latitude must be within -90 to 90"),
            ({"longitude": -180.1}, "longitude must be within -180 to 180"),
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(ValueError, message):
                    TelemetryPayload.from_dict(valid_telemetry(**overrides))


class ComputeHealthTests(unittest.TestCase):
    def test_health_thresholds(self):
        good = {
            "temperature": 40,
            "pack_voltage": 44,
            "cell_voltages": [3.45] * 16,
        }
        self.assertEqual(compute_health(None), "UNKNOWN")
        self.assertEqual(compute_health(good), "GOOD")
        self.assertEqual(compute_health({**good, "temperature": 40.1}), "WARNING")
        self.assertEqual(
            compute_health({**good, "cell_voltages": [3.4] + [3.49] * 15}),
            "WARNING",
        )
        self.assertEqual(compute_health({**good, "pack_voltage": 43.99}), "CRITICAL")
        self.assertEqual(compute_health({**good, "pack_voltage": 58.01}), "CRITICAL")


if __name__ == "__main__":
    unittest.main()
