def test_health_and_batteries_endpoints(app_client):
    health_response = app_client.get("/health")
    batteries_response = app_client.get("/api/batteries")

    assert health_response.status_code == 200
    assert health_response.get_json() == {"status": "ok"}
    assert batteries_response.status_code == 200
    assert batteries_response.get_json() == {"count": 0, "items": []}


def test_ingest_telemetry_and_return_it_in_latest_endpoint(app_client, telemetry_payload):
    ingest_response = app_client.post("/api/telemetry", json=telemetry_payload())
    latest_response = app_client.get(
        "/api/telemetry/latest?device_id=battery_pack_01"
    )

    assert ingest_response.status_code == 201
    assert ingest_response.get_json()["message"] == "Telemetry stored"
    assert latest_response.status_code == 200
    assert latest_response.get_json()["device_id"] == "battery_pack_01"
    assert latest_response.get_json()["cell_voltages"] == [3.45] * 16


def test_ingest_rejects_invalid_telemetry(app_client, telemetry_payload):
    response = app_client.post(
        "/api/telemetry", json=telemetry_payload(soc=101)
    )

    assert response.status_code == 400
    assert response.get_json() == {"error": "soc must be within 0-100"}


def test_analytics_endpoint_returns_pandas_metrics(app_client, telemetry_payload):
    app_client.post(
        "/api/telemetry",
        json=telemetry_payload(pack_voltage=50, pack_current=10, soc=80),
    )
    app_client.post(
        "/api/telemetry",
        json=telemetry_payload(
            timestamp="2026-04-07T12:00:05+00:00",
            pack_voltage=54,
            pack_current=14,
            soc=90,
            temperature=42,
            alarms=["OVER_TEMPERATURE"],
        ),
    )

    response = app_client.get(
        "/api/analytics/summary?device_id=battery_pack_01"
    )
    body = response.get_json()

    assert response.status_code == 200
    assert body["count"] == 1
    assert body["sample_count"] == 2
    assert body["items"] == [
        {
            "device_id": "battery_pack_01",
            "samples": 2,
            "avg_pack_voltage": 52.0,
            "avg_pack_current": 12.0,
            "avg_soc": 85.0,
            "min_soc": 80.0,
            "max_soc": 90.0,
            "avg_temperature": 37.6,
            "max_temperature": 42.0,
            "max_cell_imbalance": 0.0,
            "alarm_events": 1,
            "health_counts": {"GOOD": 1, "WARNING": 1, "CRITICAL": 0},
        }
    ]
