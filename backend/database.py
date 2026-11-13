import json
import sqlite3
import threading
from pathlib import Path
from typing import Any


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS telemetry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    pack_voltage REAL NOT NULL,
    pack_current REAL NOT NULL,
    soc REAL NOT NULL,
    temperature REAL NOT NULL,
    cycle_count INTEGER NOT NULL,
    latitude REAL,
    longitude REAL,
    cell_voltages TEXT NOT NULL,
    alarms TEXT NOT NULL
);
"""


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self.init_db()

    def init_db(self) -> None:
        with self._lock:
            self._connection.executescript(SCHEMA_SQL)
            self._ensure_columns()
            self._connection.commit()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def _ensure_columns(self) -> None:
        existing = {
            row["name"]
            for row in self._connection.execute("PRAGMA table_info(telemetry)").fetchall()
        }
        if "latitude" not in existing:
            self._connection.execute("ALTER TABLE telemetry ADD COLUMN latitude REAL")
        if "longitude" not in existing:
            self._connection.execute("ALTER TABLE telemetry ADD COLUMN longitude REAL")

    def insert_telemetry(self, payload: dict[str, Any]) -> int:
        query = """
            INSERT INTO telemetry (
                device_id, timestamp, pack_voltage, pack_current, soc,
                temperature, cycle_count, latitude, longitude, cell_voltages, alarms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        values = (
            payload["device_id"],
            payload["timestamp"],
            payload["pack_voltage"],
            payload["pack_current"],
            payload["soc"],
            payload["temperature"],
            payload["cycle_count"],
            payload.get("latitude"),
            payload.get("longitude"),
            json.dumps(payload["cell_voltages"]),
            json.dumps(payload["alarms"]),
        )
        with self._lock:
            cursor = self._connection.execute(query, values)
            self._connection.commit()
            return int(cursor.lastrowid)

    def fetch_latest(self, device_id: str | None = None) -> dict[str, Any] | None:
        if device_id:
            query = "SELECT * FROM telemetry WHERE device_id = ? ORDER BY id DESC LIMIT 1"
            params = (device_id,)
        else:
            query = "SELECT * FROM telemetry ORDER BY id DESC LIMIT 1"
            params = ()

        with self._lock:
            row = self._connection.execute(query, params).fetchone()
        return self._row_to_dict(row) if row else None

    def fetch_history(
        self, limit: int = 100, device_id: str | None = None
    ) -> list[dict[str, Any]]:
        if device_id:
            query = "SELECT * FROM telemetry WHERE device_id = ? ORDER BY id DESC LIMIT ?"
            params = (device_id, limit)
        else:
            query = "SELECT * FROM telemetry ORDER BY id DESC LIMIT ?"
            params = (limit,)

        with self._lock:
            rows = self._connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def fetch_latest_by_device(self, limit: int = 100) -> list[dict[str, Any]]:
        query = """
            SELECT t.*
            FROM telemetry t
            INNER JOIN (
                SELECT device_id, MAX(id) AS max_id
                FROM telemetry
                GROUP BY device_id
            ) latest ON t.id = latest.max_id
            ORDER BY t.device_id ASC
            LIMIT ?
        """
        with self._lock:
            rows = self._connection.execute(query, (limit,)).fetchall()
        return [self._row_to_dict(row) for row in rows]

    def fetch_by_time_range(
        self, start_ts: str, end_ts: str, device_id: str | None = None
    ) -> list[dict[str, Any]]:
        if device_id:
            query = """
                SELECT * FROM telemetry
                WHERE timestamp >= ? AND timestamp < ? AND device_id = ?
                ORDER BY timestamp ASC
            """
            params = (start_ts, end_ts, device_id)
        else:
            query = """
                SELECT * FROM telemetry
                WHERE timestamp >= ? AND timestamp < ?
                ORDER BY device_id ASC, timestamp ASC
            """
            params = (start_ts, end_ts)

        with self._lock:
            rows = self._connection.execute(query, params).fetchall()
        return [self._row_to_dict(row) for row in rows]

    @staticmethod
    def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "device_id": row["device_id"],
            "timestamp": row["timestamp"],
            "pack_voltage": row["pack_voltage"],
            "pack_current": row["pack_current"],
            "soc": row["soc"],
            "temperature": row["temperature"],
            "cycle_count": row["cycle_count"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "cell_voltages": json.loads(row["cell_voltages"]),
            "alarms": json.loads(row["alarms"]),
        }
