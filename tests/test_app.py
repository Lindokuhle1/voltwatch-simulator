import csv
import io


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


def test_daily_summary_calculates_state_hours_and_trips(app_client, telemetry_payload):
    readings = [
        ("2026-04-07T12:00:00+00:00", 10.0),
        ("2026-04-07T12:30:00+00:00", 0.0),
        ("2026-04-07T13:30:00+00:00", -4.0),
        ("2026-04-07T14:00:00+00:00", 10.0),
    ]
    for timestamp, current in readings:
        response = app_client.post(
            "/api/telemetry",
            json=telemetry_payload(timestamp=timestamp, pack_current=current),
        )
        assert response.status_code == 201

    response = app_client.get(
        "/api/battery/daily-summary?device_id=battery_pack_01&date=2026-04-07"
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "device_id": "battery_pack_01",
        "date": "2026-04-07",
        "samples": 4,
        "trips": 2,
        "operating_hours": 0.5,
        "idle_hours": 1.0,
        "charging_hours": 0.5,
    }


def test_daily_summary_validates_required_device_and_date(app_client):
    missing_device = app_client.get("/api/battery/daily-summary?date=2026-04-07")
    invalid_date = app_client.get(
        "/api/battery/daily-summary?device_id=battery_pack_01&date=2026-02-30"
    )

    assert missing_device.status_code == 400
    assert missing_device.get_json() == {"error": "device_id is required"}
    assert invalid_date.status_code == 400
    assert invalid_date.get_json() == {
        "error": "Invalid date format. Use YYYY-MM-DD."
    }


def test_monthly_report_exports_csv_for_all_devices(app_client, telemetry_payload):
    app_client.post(
        "/api/telemetry",
        json=telemetry_payload(
            device_id="battery_pack_02",
            pack_voltage=50,
            timestamp="2026-04-08T12:00:00+00:00",
            alarms=["CELL_IMBALANCE"],
        ),
    )
    app_client.post(
        "/api/telemetry",
        json=telemetry_payload(
            timestamp="2026-04-07T12:00:00+00:00",
            pack_voltage=54,
            pack_current=16,
            soc=80,
            temperature=42,
            alarms=["OVER_TEMPERATURE", "CELL_IMBALANCE"],
        ),
    )
    app_client.post(
        "/api/telemetry",
        json=telemetry_payload(
            timestamp="2026-05-01T00:00:00+00:00",
            pack_voltage=58,
        ),
    )

    response = app_client.get("/api/reports/monthly?month=2026-04")
    rows = list(csv.DictReader(io.StringIO(response.get_data(as_text=True))))

    assert response.status_code == 200
    assert response.mimetype == "text/csv"
    assert response.headers["Content-Disposition"].endswith(
        "voltwatch_monthly_report_2026-04_all_batteries.csv"
    )
    assert [row["device_id"] for row in rows] == [
        "battery_pack_01",
        "battery_pack_02",
    ]
    first = rows[0]
    assert first["samples"] == "1"
    assert first["avg_pack_voltage"] == "54.0"
    assert first["alarm_events"] == "2"
    assert first["last_cycle_count"] == "4"


def test_monthly_report_filters_device_and_rejects_invalid_month(
    app_client, telemetry_payload
):
    app_client.post("/api/telemetry", json=telemetry_payload())
    app_client.post(
        "/api/telemetry",
        json=telemetry_payload(device_id="battery_pack_02"),
    )

    filtered_response = app_client.get(
        "/api/reports/monthly?month=2026-04&device_id=battery_pack_02"
    )
    filtered_rows = list(
        csv.DictReader(io.StringIO(filtered_response.get_data(as_text=True)))
    )
    invalid_response = app_client.get("/api/reports/monthly?month=2026-13")

    assert [row["device_id"] for row in filtered_rows] == ["battery_pack_02"]
    assert filtered_response.headers["Content-Disposition"].endswith(
        "voltwatch_monthly_report_2026-04_battery_pack_02.csv"
    )
    assert invalid_response.status_code == 400
    assert invalid_response.get_json() == {
        "error": "Invalid month format. Use YYYY-MM."
    }


def test_powerbi_export_flattens_cells_alarms_and_health(
    app_client, telemetry_payload
):
    app_client.post(
        "/api/telemetry",
        json=telemetry_payload(
            cell_voltages=[3.4] + [3.51] * 15,
            alarms=["CELL_IMBALANCE", "OVER_TEMPERATURE"],
            temperature=41,
        ),
    )
    app_client.post(
        "/api/telemetry",
        json=telemetry_payload(
            timestamp="2026-04-07T12:00:05+00:00",
            device_id="battery_pack_02",
            pack_voltage=43,
        ),
    )

    response = app_client.get(
        "/api/powerbi/telemetry?device_id=battery_pack_01&start=2026-04-07T00:00:00%2B00:00&end=2026-04-08T00:00:00%2B00:00"
    )
    body = response.get_json()
    item = body["items"][0]

    assert response.status_code == 200
    assert body["count"] == 1
    assert item["cell_01"] == 3.4
    assert item["cell_16"] == 3.51
    assert item["alarms_count"] == 2
    assert item["alarms_text"] == "CELL_IMBALANCE,OVER_TEMPERATURE"
    assert item["health"] == "WARNING"
    assert body["generated_at"]
