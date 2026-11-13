import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app import Config, create_app


class AppSmokeTest(unittest.TestCase):
    def test_health_and_batteries_endpoints(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "test.db"
            with patch.object(Config, "DATABASE_PATH", str(database_path)):
                app = create_app()

            with app.test_client() as client:
                health_response = client.get("/health")
                batteries_response = client.get("/api/batteries")

        self.assertEqual(health_response.status_code, 200)
        self.assertEqual(health_response.get_json(), {"status": "ok"})
        self.assertEqual(batteries_response.status_code, 200)
        self.assertEqual(batteries_response.get_json(), {"count": 0, "items": []})


if __name__ == "__main__":
    unittest.main()
