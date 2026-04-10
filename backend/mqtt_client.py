import json
import uuid

import paho.mqtt.client as mqtt


class MqttPublisher:
    def __init__(self, broker: str, port: int, topic: str) -> None:
        client_id = f"voltwatch-{uuid.uuid4()}"
        self.topic = topic
        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        self.client.connect(broker, port, keepalive=60)
        self.client.loop_start()

    def publish(self, payload: dict) -> None:
        message = json.dumps(payload)
        self.client.publish(self.topic, message, qos=0, retain=False)

    def close(self) -> None:
        self.client.loop_stop()
        self.client.disconnect()
