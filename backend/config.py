import os


class Config:
    DATABASE_PATH = os.getenv("DATABASE_PATH", "voltwatch.db")
    MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
    MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
    MQTT_TOPIC = os.getenv("MQTT_TOPIC", "voltwatch/battery/telemetry")
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "5000"))
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
