import json
import threading
from typing import Any

from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import Engine, URL
from sqlalchemy.pool import StaticPool


metadata = MetaData()
telemetry = Table(
    "telemetry",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("device_id", String, nullable=False, index=True),
    Column("timestamp", String, nullable=False, index=True),
    Column("pack_voltage", Float, nullable=False),
    Column("pack_current", Float, nullable=False),
    Column("soc", Float, nullable=False),
    Column("temperature", Float, nullable=False),
    Column("cycle_count", Integer, nullable=False),
    Column("latitude", Float),
    Column("longitude", Float),
    Column("cell_voltages", Text, nullable=False),
    Column("alarms", Text, nullable=False),
)


class Database:
    def __init__(self, database_url: str) -> None:
        self._lock = threading.Lock()
        if "://" not in database_url and database_url != ":memory:":
            database_url = URL.create("sqlite", database=database_url).render_as_string(
                hide_password=False
            )
        elif database_url == ":memory:":
            database_url = "sqlite:///:memory:"

        engine_options: dict[str, Any] = {"future": True}
        if database_url.startswith("sqlite:"):
            engine_options["connect_args"] = {"check_same_thread": False}
            if database_url.endswith(":memory:"):
                engine_options["poolclass"] = StaticPool

        self.engine: Engine = create_engine(database_url, **engine_options)
        self.init_db()

    def init_db(self) -> None:
        metadata.create_all(self.engine)
        existing = {column["name"] for column in inspect(self.engine).get_columns("telemetry")}
        with self.engine.begin() as connection:
            for name in ("latitude", "longitude"):
                if name not in existing:
                    connection.execute(text(f"ALTER TABLE telemetry ADD COLUMN {name} FLOAT"))

    def close(self) -> None:
        self.engine.dispose()

    @staticmethod
    def _row_to_dict(row: Any) -> dict[str, Any]:
        record = dict(row)
        record["cell_voltages"] = json.loads(record["cell_voltages"])
        record["alarms"] = json.loads(record["alarms"])
        return record

    def insert_telemetry(self, payload: dict[str, Any]) -> int:
        values = {
            "device_id": payload["device_id"],
            "timestamp": payload["timestamp"],
            "pack_voltage": payload["pack_voltage"],
            "pack_current": payload["pack_current"],
            "soc": payload["soc"],
            "temperature": payload["temperature"],
            "cycle_count": payload["cycle_count"],
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "cell_voltages": json.dumps(payload["cell_voltages"]),
            "alarms": json.dumps(payload["alarms"]),
        }
        with self._lock, self.engine.begin() as connection:
            result = connection.execute(telemetry.insert().values(**values))
            return int(result.inserted_primary_key[0])

    def fetch_latest(self, device_id: str | None = None) -> dict[str, Any] | None:
        query = select(telemetry).order_by(telemetry.c.id.desc()).limit(1)
        if device_id:
            query = query.where(telemetry.c.device_id == device_id)

        with self._lock, self.engine.connect() as connection:
            row = connection.execute(query).mappings().first()
        return self._row_to_dict(row) if row else None

    def fetch_history(
        self, limit: int = 100, device_id: str | None = None
    ) -> list[dict[str, Any]]:
        query = select(telemetry).order_by(telemetry.c.id.desc()).limit(limit)
        if device_id:
            query = query.where(telemetry.c.device_id == device_id)

        with self._lock, self.engine.connect() as connection:
            rows = connection.execute(query).mappings().all()
        return [self._row_to_dict(row) for row in rows]

    def fetch_latest_by_device(self, limit: int = 100) -> list[dict[str, Any]]:
        latest_ids = (
            select(telemetry.c.device_id, func.max(telemetry.c.id).label("latest_id"))
            .group_by(telemetry.c.device_id)
            .subquery()
        )
        query = (
            select(telemetry)
            .join(latest_ids, telemetry.c.id == latest_ids.c.latest_id)
            .order_by(telemetry.c.device_id.asc())
            .limit(limit)
        )
        with self._lock, self.engine.connect() as connection:
            rows = connection.execute(query).mappings().all()
        return [self._row_to_dict(row) for row in rows]

    def fetch_by_time_range(
        self, start_ts: str, end_ts: str, device_id: str | None = None
    ) -> list[dict[str, Any]]:
        query = (
            select(telemetry)
            .where(telemetry.c.timestamp >= start_ts, telemetry.c.timestamp < end_ts)
            .order_by(telemetry.c.timestamp.asc())
        )
        if device_id:
            query = query.where(telemetry.c.device_id == device_id)
        else:
            query = query.order_by(telemetry.c.device_id.asc(), telemetry.c.timestamp.asc())

        with self._lock, self.engine.connect() as connection:
            rows = connection.execute(query).mappings().all()
        return [self._row_to_dict(row) for row in rows]
