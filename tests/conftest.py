import pytest

from backend.app import Config, create_app
from backend.database import Database


@pytest.fixture
def telemetry_payload():
    def create_payload(**overrides):
        payload = {
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
        payload.update(overrides)
        return payload

    return create_payload


@pytest.fixture
def database():
    db = Database("sqlite:///:memory:")
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def app_client(monkeypatch, database):
    monkeypatch.setattr(Config, "DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setattr("backend.app.Database", lambda _url: database)
    app = create_app()
    with app.test_client() as client:
        yield client
