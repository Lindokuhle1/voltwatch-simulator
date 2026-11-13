from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class TelemetryPayload:
    device_id: str
    timestamp: str
    pack_voltage: float
    pack_current: float
    soc: float
    temperature: float
    cycle_count: int
    latitude: float | None = None
    longitude: float | None = None
    cell_voltages: list[float] = field(default_factory=list)
    alarms: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TelemetryPayload":
        required = [
            "device_id",
            "timestamp",
            "pack_voltage",
            "pack_current",
            "soc",
            "temperature",
            "cycle_count",
            "cell_voltages",
            "alarms",
        ]
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError(f"Missing telemetry fields: {', '.join(missing)}")

        payload = cls(
            device_id=str(data["device_id"]),
            timestamp=str(data["timestamp"]),
            pack_voltage=float(data["pack_voltage"]),
            pack_current=float(data["pack_current"]),
            soc=float(data["soc"]),
            temperature=float(data["temperature"]),
            cycle_count=int(data["cycle_count"]),
            latitude=float(data["latitude"]) if data.get("latitude") is not None else None,
            longitude=float(data["longitude"]) if data.get("longitude") is not None else None,
            cell_voltages=[float(v) for v in data["cell_voltages"]],
            alarms=[str(a) for a in data["alarms"]],
        )
        payload.validate()
        return payload

    def validate(self) -> None:
        datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        if not self.device_id:
            raise ValueError("device_id cannot be empty")
        if not 0 <= self.soc <= 100:
            raise ValueError("soc must be within 0-100")
        if len(self.cell_voltages) != 16:
            raise ValueError("cell_voltages must contain 16 values")
        if self.latitude is not None and not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be within -90 to 90")
        if self.longitude is not None and not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be within -180 to 180")

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "timestamp": self.timestamp,
            "pack_voltage": self.pack_voltage,
            "pack_current": self.pack_current,
            "soc": self.soc,
            "temperature": self.temperature,
            "cycle_count": self.cycle_count,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "cell_voltages": self.cell_voltages,
            "alarms": self.alarms,
        }


def compute_health(telemetry: dict[str, Any] | None) -> str:
    if telemetry is None:
        return "UNKNOWN"

    temperature = float(telemetry["temperature"])
    pack_voltage = float(telemetry["pack_voltage"])
    cell_voltages = telemetry["cell_voltages"]
    imbalance = round(max(cell_voltages) - min(cell_voltages), 3)

    if pack_voltage > 58 or pack_voltage < 44:
        return "CRITICAL"
    if temperature > 40 or imbalance > 0.08:
        return "WARNING"
    return "GOOD"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
