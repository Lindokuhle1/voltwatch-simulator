import csv
import io
from datetime import datetime, timezone

from flask import Blueprint, Response, jsonify, request

from .analytics import summarize_telemetry
from .models import TelemetryPayload, compute_health


def build_blueprint(db):
    api = Blueprint("api", __name__, url_prefix="/api")

    def parse_month(month_text: str) -> tuple[datetime, datetime]:
        start = datetime.strptime(month_text, "%Y-%m").replace(tzinfo=timezone.utc)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end

    @api.post("/telemetry")
    def ingest_telemetry():
        data = request.get_json(silent=True) or {}
        try:
            payload = TelemetryPayload.from_dict(data)
        except (ValueError, TypeError) as exc:
            return jsonify({"error": str(exc)}), 400

        row_id = db.insert_telemetry(payload.to_dict())
        return jsonify({"message": "Telemetry stored", "id": row_id}), 201

    @api.get("/telemetry/latest")
    def latest_telemetry():
        device_id = request.args.get("device_id", type=str)
        latest = db.fetch_latest(device_id=device_id)
        if latest is None:
            return jsonify({"message": "No telemetry data available"}), 404
        return jsonify(latest)

    @api.get("/telemetry/history")
    def telemetry_history():
        limit = request.args.get("limit", default=50, type=int)
        limit = max(1, min(limit, 500))
        device_id = request.args.get("device_id", type=str)
        history = db.fetch_history(limit=limit, device_id=device_id)
        return jsonify({"count": len(history), "items": history})

    @api.get("/powerbi/telemetry")
    def powerbi_telemetry():
        device_id = request.args.get("device_id", type=str)
        start_ts = request.args.get("start", type=str)
        end_ts = request.args.get("end", type=str)
        limit = request.args.get("limit", default=1000, type=int)
        limit = max(1, min(limit, 10000))

        if start_ts and end_ts:
            records = db.fetch_by_time_range(start_ts=start_ts, end_ts=end_ts, device_id=device_id)
        else:
            records = db.fetch_history(limit=limit, device_id=device_id)
            records = list(reversed(records))

        items = []
        for row in records:
            flat_row = {
                "id": row["id"],
                "device_id": row["device_id"],
                "timestamp": row["timestamp"],
                "pack_voltage": row["pack_voltage"],
                "pack_current": row["pack_current"],
                "soc": row["soc"],
                "temperature": row["temperature"],
                "cycle_count": row["cycle_count"],
                "latitude": row.get("latitude"),
                "longitude": row.get("longitude"),
                "alarms_count": len(row["alarms"]),
                "alarms_text": ",".join(row["alarms"]),
                "health": compute_health(row),
            }

            for idx, value in enumerate(row.get("cell_voltages", []), start=1):
                flat_row[f"cell_{idx:02d}"] = value

            items.append(flat_row)

        return jsonify(
            {
                "count": len(items),
                "items": items,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    @api.get("/battery/status")
    def battery_status():
        device_id = request.args.get("device_id", type=str)
        latest = db.fetch_latest(device_id=device_id)
        if latest is None:
            return jsonify({"health": "UNKNOWN", "latest": None}), 200

        return jsonify(
            {
                "health": compute_health(latest),
                "latest": latest,
            }
        )

    @api.get("/batteries")
    def battery_list():
        limit = request.args.get("limit", default=100, type=int)
        limit = max(1, min(limit, 500))
        latest_rows = db.fetch_latest_by_device(limit=limit)

        items = []
        for row in latest_rows:
            cell_voltages = row["cell_voltages"]
            cell_max = max(cell_voltages)
            cell_min = min(cell_voltages)
            imbalance = cell_max - cell_min
            items.append(
                {
                    "id": row["id"],
                    "device_id": row["device_id"],
                    "soc": row["soc"],
                    "pack_voltage": row["pack_voltage"],
                    "pack_current": row["pack_current"],
                    "temperature": row["temperature"],
                    "cycle_count": row["cycle_count"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "cell_max": cell_max,
                    "cell_min": cell_min,
                    "cell_imbalance": imbalance,
                    "active": row["pack_current"] > 0,
                    "last_activity": row["timestamp"],
                    "alarm_count": len(row["alarms"]),
                    "alarms": row["alarms"],
                    "health": compute_health(row),
                }
            )

        return jsonify({"count": len(items), "items": items})

    @api.get("/analytics/summary")
    def analytics_summary():
        limit = request.args.get("limit", default=1000, type=int)
        limit = max(1, min(limit, 10000))
        device_id = request.args.get("device_id", type=str)
        records = db.fetch_history(limit=limit, device_id=device_id)
        items = summarize_telemetry(records)
        return jsonify(
            {
                "count": len(items),
                "sample_count": sum(item["samples"] for item in items),
                "items": items,
            }
        )

    @api.get("/reports/monthly")
    def monthly_report():
        month = request.args.get("month", default=datetime.now(timezone.utc).strftime("%Y-%m"), type=str)
        device_id = request.args.get("device_id", type=str)

        try:
            start_dt, end_dt = parse_month(month)
        except ValueError:
            return jsonify({"error": "Invalid month format. Use YYYY-MM."}), 400

        records = db.fetch_by_time_range(
            start_ts=start_dt.isoformat(),
            end_ts=end_dt.isoformat(),
            device_id=device_id,
        )

        grouped: dict[str, dict] = {}
        for row in records:
            did = row["device_id"]
            stats = grouped.setdefault(
                did,
                {
                    "samples": 0,
                    "sum_voltage": 0.0,
                    "sum_current": 0.0,
                    "sum_soc": 0.0,
                    "sum_temp": 0.0,
                    "min_soc": 100.0,
                    "max_temp": float("-inf"),
                    "max_imbalance": 0.0,
                    "alarm_events": 0,
                    "last_cycle_count": 0,
                    "last_timestamp": "",
                },
            )

            stats["samples"] += 1
            stats["sum_voltage"] += float(row["pack_voltage"])
            stats["sum_current"] += float(row["pack_current"])
            stats["sum_soc"] += float(row["soc"])
            stats["sum_temp"] += float(row["temperature"])
            stats["min_soc"] = min(stats["min_soc"], float(row["soc"]))
            stats["max_temp"] = max(stats["max_temp"], float(row["temperature"]))
            imbalance = max(row["cell_voltages"]) - min(row["cell_voltages"])
            stats["max_imbalance"] = max(stats["max_imbalance"], imbalance)
            stats["alarm_events"] += len(row["alarms"])
            stats["last_cycle_count"] = max(stats["last_cycle_count"], int(row["cycle_count"]))
            stats["last_timestamp"] = max(stats["last_timestamp"], row["timestamp"])

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "month",
                "device_id",
                "samples",
                "avg_pack_voltage",
                "avg_pack_current",
                "avg_soc",
                "avg_temperature",
                "min_soc",
                "max_temperature",
                "max_cell_imbalance",
                "alarm_events",
                "last_cycle_count",
                "last_timestamp",
            ]
        )

        for did in sorted(grouped.keys()):
            stats = grouped[did]
            samples = max(1, stats["samples"])
            writer.writerow(
                [
                    month,
                    did,
                    stats["samples"],
                    round(stats["sum_voltage"] / samples, 3),
                    round(stats["sum_current"] / samples, 3),
                    round(stats["sum_soc"] / samples, 3),
                    round(stats["sum_temp"] / samples, 3),
                    round(stats["min_soc"], 3),
                    round(stats["max_temp"], 3),
                    round(stats["max_imbalance"], 4),
                    stats["alarm_events"],
                    stats["last_cycle_count"],
                    stats["last_timestamp"],
                ]
            )

        suffix = device_id or "all_batteries"
        filename = f"voltwatch_monthly_report_{month}_{suffix}.csv"
        return Response(
            buffer.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @api.get("/battery/daily-summary")
    def battery_daily_summary():
        device_id = request.args.get("device_id", type=str)
        if not device_id:
            return jsonify({"error": "device_id is required"}), 400

        date_text = request.args.get(
            "date",
            default=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            type=str,
        )
        try:
            start_dt = datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

        end_dt = start_dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        records = db.fetch_by_time_range(
            start_ts=start_dt.isoformat(),
            end_ts=end_dt.isoformat(),
            device_id=device_id,
        )

        def classify_state(pack_current: float) -> str:
            if pack_current < -2.0:
                return "charging"
            if abs(pack_current) <= 2.0:
                return "idle"
            return "operating"

        operating_hours = 0.0
        idle_hours = 0.0
        charging_hours = 0.0
        trips = 0
        prev_state = None

        for record in records:
            state = classify_state(float(record["pack_current"]))
            if state == "operating" and prev_state != "operating":
                trips += 1
            prev_state = state

        for idx in range(len(records) - 1):
            current = records[idx]
            next_row = records[idx + 1]

            t0 = datetime.fromisoformat(current["timestamp"].replace("Z", "+00:00"))
            t1 = datetime.fromisoformat(next_row["timestamp"].replace("Z", "+00:00"))
            delta_hours = max(0.0, (t1 - t0).total_seconds() / 3600.0)

            state = classify_state(float(current["pack_current"]))
            if state == "operating":
                operating_hours += delta_hours
            elif state == "idle":
                idle_hours += delta_hours
            else:
                charging_hours += delta_hours

        return jsonify(
            {
                "device_id": device_id,
                "date": date_text,
                "samples": len(records),
                "trips": trips,
                "operating_hours": round(operating_hours, 3),
                "idle_hours": round(idle_hours, 3),
                "charging_hours": round(charging_hours, 3),
            }
        )

    return api
