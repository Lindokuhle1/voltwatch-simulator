import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app import Config, create_app
from backend.database import Database


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


class AppSmokeTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir_context = tempfile.TemporaryDirectory()
        database_path = Path(self.temp_dir_context.name) / "test.db"
        self.db = Database(str(database_path))
        with patch.object(Config, "DATABASE_PATH", str(database_path)):
            with patch("backend.app.Database", return_value=self.db):
                self.app = create_app()

    def tearDown(self):
        self.db.close()
        self.temp_dir_context.cleanup()

    def test_health_and_batteries_endpoints(self):
        with self.app.test_client() as client:
            health_response = client.get("/health")
            batteries_response = client.get("/api/batteries")

        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.get_json(), {"status": "ok"})
        self.assertEqual(batteries_response.status_code, 200)
        self.assertEqual(batteries_response.get_json(), {"count": 0, "items": []})

    def test_ingest_telemetry_and_return_it_in_latest_endpoint(self):
        with self.app.test_client() as client:
            ingest_response = client.post(
                "/api/telemetry", json=valid_telemetry()
            )
            latest_response = client.get(
                "/api/telemetry/latest?device_id=battery_pack_01"
            )

        self.assertEqual(ingest_response.status_code, 201)
        self.assertEqual(ingest_response.get_json()["message"], "Telemetry stored")
        self.assertEqual(latest_response.status_code, 200)
        self.assertEqual(latest_response.get_json()["device_id"], "battery_pack_01")
        self.assertEqual(latest_response.get_json()["cell_voltages"], [3.45] * 16)

    def test_ingest_rejects_invalid_telemetry(self):
        with self.app.test_client() as client:
            response = client.post(
                "/api/telemetry", json=valid_telemetry(soc=101)
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {"error": "soc must be within 0-100"})


if __name__ == "__main__":
    unittest.main()
