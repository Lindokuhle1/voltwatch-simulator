import os


class Config:
    DEFAULT_DATABASE_URL = "postgresql+psycopg://voltwatch:voltwatch@localhost:5433/voltwatch"
    DATABASE_URL = os.getenv(
        "DATABASE_URL", os.getenv("DATABASE_PATH", DEFAULT_DATABASE_URL)
    )
    MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
    MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
    MQTT_TOPIC = os.getenv("MQTT_TOPIC", "voltwatch/battery/telemetry")
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "5000"))
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
