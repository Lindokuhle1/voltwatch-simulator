import unittest

from backend.database import Database


def telemetry(device_id, timestamp, voltage):
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


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")

    def tearDown(self):
        self.db.close()

    def test_insert_and_fetch_latest(self):
        first_id = self.db.insert_telemetry(
            telemetry("battery_pack_01", "2026-04-07T12:00:00+00:00", 52.0)
        )
        self.db.insert_telemetry(
            telemetry("battery_pack_01", "2026-04-07T12:00:05+00:00", 53.0)
        )

        latest = self.db.fetch_latest()
        self.assertGreater(latest["id"], first_id)
        self.assertEqual(latest["pack_voltage"], 53.0)
        self.assertEqual(latest["cell_voltages"], [3.45] * 16)
        self.assertEqual(self.db.fetch_latest("battery_pack_02"), None)

    def test_fetch_history_filters_device_and_limit(self):
        for index in range(3):
            self.db.insert_telemetry(
                telemetry(
                    "battery_pack_01",
                    f"2026-04-07T12:00:0{index}+00:00",
                    52.0 + index,
                )
            )
        self.db.insert_telemetry(
            telemetry("battery_pack_02", "2026-04-07T12:00:03+00:00", 54.0)
        )

        history = self.db.fetch_history(limit=2, device_id="battery_pack_01")

        self.assertEqual([row["pack_voltage"] for row in history], [54.0, 53.0])

    def test_fetch_latest_by_device_returns_one_latest_row_per_device(self):
        self.db.insert_telemetry(
            telemetry("battery_pack_02", "2026-04-07T12:00:00+00:00", 51.0)
        )
        self.db.insert_telemetry(
            telemetry("battery_pack_01", "2026-04-07T12:00:01+00:00", 52.0)
        )
        self.db.insert_telemetry(
            telemetry("battery_pack_02", "2026-04-07T12:00:02+00:00", 53.0)
        )

        latest = self.db.fetch_latest_by_device()

        self.assertEqual(
            [(row["device_id"], row["pack_voltage"]) for row in latest],
            [("battery_pack_01", 52.0), ("battery_pack_02", 53.0)],
        )

    def test_fetch_by_time_range_uses_exclusive_end(self):
        for timestamp in (
            "2026-04-07T12:00:00+00:00",
            "2026-04-07T12:00:01+00:00",
            "2026-04-07T12:00:02+00:00",
        ):
            self.db.insert_telemetry(telemetry("battery_pack_01", timestamp, 52.0))

        records = self.db.fetch_by_time_range(
            "2026-04-07T12:00:00+00:00",
            "2026-04-07T12:00:02+00:00",
            device_id="battery_pack_01",
        )

        self.assertEqual(
            [row["timestamp"] for row in records],
            ["2026-04-07T12:00:00+00:00", "2026-04-07T12:00:01+00:00"],
        )


if __name__ == "__main__":
    unittest.main()
