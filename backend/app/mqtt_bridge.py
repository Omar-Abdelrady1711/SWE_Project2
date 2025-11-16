"""Simple MQTT bridge using paho-mqtt.

This is a minimal, single-file MQTT bridge implementation.
It can be expanded to translate MQTT messages into DB writes
and to publish commands from the API.
"""
from paho.mqtt.client import Client
import os
import threading
import json
from typing import Optional

_client: Optional[Client] = None

def _on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe("aquarium/+/sensor/#")


def _on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
    except Exception:
        payload = str(msg.payload)
    # placeholder: real implementation would parse and insert into DB
    print(f"MQTT message {msg.topic} -> {payload}")


def start_bridge(broker: str = None, port: int = None):
    global _client
    broker = broker or os.environ.get("MQTT_BROKER", "test.mosquitto.org")
    port = int(port or os.environ.get("MQTT_PORT", 1883))
    _client = Client()
    _client.on_connect = _on_connect
    _client.on_message = _on_message
    _client.connect(broker, port)
    thread = threading.Thread(target=_client.loop_forever, daemon=True)
    thread.start()
    print(f"Started MQTT bridge to {broker}:{port}")


def publish(topic: str, payload: str):
    if _client:
        _client.publish(topic, payload)
    else:
        raise RuntimeError("MQTT bridge not started")
