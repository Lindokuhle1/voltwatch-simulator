import random
import time
import math
from hashlib import sha256
from datetime import datetime, timezone
from typing import Any

import requests

from .models import compute_health
from .mqtt_client import MqttPublisher


class BatteryTelemetrySimulator:
    def __init__(
        self,
        api_url: str,
        mqtt_broker: str,
        mqtt_port: int,
        mqtt_topic: str,
        device_id: str = "battery_pack_01",
        mqtt_publisher: MqttPublisher | None = None,
    ) -> None:
        self.api_url = api_url.rstrip("/")
        self.device_id = device_id
        self._owns_mqtt = mqtt_publisher is None
        self.mqtt = mqtt_publisher or MqttPublisher(mqtt_broker, mqtt_port, mqtt_topic)
        seed = int.from_bytes(sha256(device_id.encode("utf-8")).digest()[:8], "big")
        self.rng = random.Random(seed)

        # Device-specific profile makes each battery stream distinct telemetry.
        self.soc = round(self.rng.uniform(40.0, 100.0), 2)
        self.current_bias = self.rng.uniform(-8.0, 8.0)
        self.temperature_bias = self.rng.uniform(-4.0, 4.0)
        self.cell_base_bias = self.rng.uniform(-0.07, 0.07)
        self.heading_deg = self.rng.uniform(0, 360)
        self.latitude = self.rng.uniform(-34.0, -22.0)
        self.longitude = self.rng.uniform(16.0, 33.0)
        self.cycle_count = 0
        self.discharge_mode = self.soc > 10
        self._completed_discharge = False

    def _update_location(self, speed_kph: float) -> None:
        # Approximate movement per sample interval for a realistic map drift.
        interval_seconds = 5.0
        distance_km = abs(speed_kph) * (interval_seconds / 3600.0)
        distance_deg = distance_km / 111.0

        self.heading_deg = (self.heading_deg + self.rng.uniform(-7.0, 7.0)) % 360
        heading_rad = math.radians(self.heading_deg)

        lat_delta = distance_deg * math.cos(heading_rad)
        lon_scale = max(0.2, math.cos(math.radians(self.latitude)))
        lon_delta = (distance_deg * math.sin(heading_rad)) / lon_scale

        self.latitude = max(-89.0, min(89.0, self.latitude + lat_delta))
        self.longitude = ((self.longitude + lon_delta + 180.0) % 360.0) - 180.0

    def _generate_cell_voltages(self) -> list[float]:
        base = self.rng.uniform(3.45, 3.62) + self.cell_base_bias
        cells = [round(base + self.rng.uniform(-0.04, 0.04), 3) for _ in range(16)]
        return [min(3.7, max(3.4, v)) for v in cells]

    def _generate_telemetry(self) -> dict[str, Any]:
        if self.discharge_mode:
            self.soc = max(0.0, self.soc - self.rng.uniform(0.05, 0.25))
        else:
            self.soc = min(100.0, self.soc + self.rng.uniform(0.1, 0.3))

        if self.soc <= 5:
            self.discharge_mode = False
            self._completed_discharge = True
        elif self.soc >= 98:
            if self._completed_discharge:
                self.cycle_count += 1
                self._completed_discharge = False
            self.discharge_mode = True

        pack_current = round(
            min(40.0, max(-20.0, self.rng.uniform(-20.0, 40.0) + self.current_bias)), 2
        )
        temperature = round(
            min(45.0, max(25.0, self.rng.uniform(25.0, 45.0) + self.temperature_bias)), 2
        )
        self._update_location(pack_current)
        cell_voltages = self._generate_cell_voltages()
        pack_voltage = round(sum(cell_voltages), 2)

        alarms = self._detect_alarms(pack_voltage, temperature, cell_voltages)

        payload = {
            "device_id": self.device_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pack_voltage": pack_voltage,
            "pack_current": pack_current,
            "soc": round(self.soc, 2),
            "temperature": temperature,
            "cycle_count": self.cycle_count,
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
            "cell_voltages": cell_voltages,
            "alarms": alarms,
        }
        payload["health"] = compute_health(payload)
        return payload

    @staticmethod
    def _detect_alarms(
        pack_voltage: float, temperature: float, cell_voltages: list[float]
    ) -> list[str]:
        alarms = []
        if temperature > 45:
            alarms.append("OVER_TEMPERATURE")
        if pack_voltage > 58:
            alarms.append("PACK_OVER_VOLTAGE")
        if pack_voltage < 44:
            alarms.append("PACK_UNDER_VOLTAGE")

        cell_imbalance = max(cell_voltages) - min(cell_voltages)
        if cell_imbalance > 0.1:
            alarms.append("CELL_IMBALANCE")

        return alarms

    def push_once(self) -> dict[str, Any]:
        payload = self._generate_telemetry()
        self.mqtt.publish(payload)
        requests.post(f"{self.api_url}/api/telemetry", json=payload, timeout=10)
        return payload

    def run_forever(self, interval_seconds: int = 5) -> None:
        print("Starting VoltWatch simulator loop...")
        try:
            while True:
                payload = self.push_once()
                print(
                    f"{payload['timestamp']} | V={payload['pack_voltage']}V | "
                    f"I={payload['pack_current']}A | SOC={payload['soc']}% | "
                    f"T={payload['temperature']}C | health={payload['health']}"
                )
                time.sleep(interval_seconds)
        finally:
            if self._owns_mqtt:
                self.mqtt.close()


class BatteryFleetSimulator:
    def __init__(
        self,
        api_url: str,
        mqtt_broker: str,
        mqtt_port: int,
        mqtt_topic: str,
        battery_count: int = 10,
        device_prefix: str = "battery_pack_",
    ) -> None:
        self.battery_count = max(10, battery_count)
        self.mqtt = MqttPublisher(mqtt_broker, mqtt_port, mqtt_topic)
        self.simulators: list[BatteryTelemetrySimulator] = []

        for index in range(1, self.battery_count + 1):
            device_id = f"{device_prefix}{index:02d}"
            self.simulators.append(
                BatteryTelemetrySimulator(
                    api_url=api_url,
                    mqtt_broker=mqtt_broker,
                    mqtt_port=mqtt_port,
                    mqtt_topic=mqtt_topic,
                    device_id=device_id,
                    mqtt_publisher=self.mqtt,
                )
            )

    def push_once(self) -> list[dict[str, Any]]:
        return [simulator.push_once() for simulator in self.simulators]

    def run_forever(self, interval_seconds: int = 5) -> None:
        print(f"Starting VoltWatch fleet simulator loop ({self.battery_count} batteries)...")
        try:
            while True:
                payloads = self.push_once()
                sample = payloads[0]
                print(
                    f"{sample['timestamp']} | sent={len(payloads)} devices | "
                    f"sample={sample['device_id']} | V={sample['pack_voltage']}V | "
                    f"SOC={sample['soc']}% | health={sample['health']}"
                )
                time.sleep(interval_seconds)
        finally:
            self.mqtt.close()
