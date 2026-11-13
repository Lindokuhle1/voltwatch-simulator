from typing import Any

import pandas as pd

from .models import compute_health


def summarize_telemetry(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not records:
        return []

    frame = pd.DataFrame.from_records(records)
    frame["cell_imbalance"] = frame["cell_voltages"].map(
        lambda values: max(values) - min(values)
    )
    frame["alarm_count"] = frame["alarms"].map(len)
    frame["health"] = [compute_health(record) for record in records]

    grouped = frame.groupby("device_id", sort=True)
    result = grouped.agg(
        samples=("id", "count"),
        avg_pack_voltage=("pack_voltage", "mean"),
        avg_pack_current=("pack_current", "mean"),
        avg_soc=("soc", "mean"),
        min_soc=("soc", "min"),
        max_soc=("soc", "max"),
        avg_temperature=("temperature", "mean"),
        max_temperature=("temperature", "max"),
        max_cell_imbalance=("cell_imbalance", "max"),
        alarm_events=("alarm_count", "sum"),
    )

    summaries = []
    for device_id, values in result.iterrows():
        health_counts = (
            grouped.get_group(device_id)["health"].value_counts().to_dict()
        )
        summaries.append(
            {
                "device_id": device_id,
                "samples": int(values["samples"]),
                "avg_pack_voltage": round(float(values["avg_pack_voltage"]), 3),
                "avg_pack_current": round(float(values["avg_pack_current"]), 3),
                "avg_soc": round(float(values["avg_soc"]), 3),
                "min_soc": round(float(values["min_soc"]), 3),
                "max_soc": round(float(values["max_soc"]), 3),
                "avg_temperature": round(float(values["avg_temperature"]), 3),
                "max_temperature": round(float(values["max_temperature"]), 3),
                "max_cell_imbalance": round(float(values["max_cell_imbalance"]), 4),
                "alarm_events": int(values["alarm_events"]),
                "health_counts": {
                    health: int(health_counts.get(health, 0))
                    for health in ("GOOD", "WARNING", "CRITICAL")
                },
            }
        )
    return summaries
