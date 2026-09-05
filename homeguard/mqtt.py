"""Paho v2 client wrapper. Subscriptions are restored after reconnect."""
import logging
import threading
import uuid
import paho.mqtt.client as mqtt
from .config import HOST, PORT
from .protocol import encode

class Bus:
    def __init__(self, name, subscriptions=(), on_message=None, on_status=None):
        self.name = name
        self.subscriptions = list(subscriptions)
        self.handler = on_message
        self.status_handler = on_status
        self.ready = threading.Event()
        self.pending_subscriptions = set()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=f"homeguard-{name}-{uuid.uuid4().hex[:8]}")
        self.client.on_connect = self._connect
        self.client.on_disconnect = self._disconnect
        self.client.on_message = self._message
        self.client.on_subscribe = self._subscribe
        self.client.reconnect_delay_set(min_delay=1, max_delay=5)

    def _connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            logging.error("%s connection rejected: %s", self.name, reason_code)
            return
        self.pending_subscriptions.clear()
        for name in self.subscriptions:
            result, mid = client.subscribe(name, qos=1)
            if result != mqtt.MQTT_ERR_SUCCESS:
                logging.error("%s subscription failed: %s", self.name, name)
                return
            self.pending_subscriptions.add(mid)
        if not self.pending_subscriptions:
            self._ready()

    def _subscribe(self, client, userdata, mid, reason_codes, properties):
        if any(code.is_failure for code in reason_codes):
            logging.error("%s subscription rejected", self.name)
            return
        self.pending_subscriptions.discard(mid)
        if not self.pending_subscriptions:
            self._ready()

    def _ready(self):
        self.ready.set()
        if self.status_handler:
            self.status_handler(True)

    def _disconnect(self, client, userdata, flags, reason_code, properties):
        self.ready.clear()
        self.pending_subscriptions.clear()
        if self.status_handler:
            self.status_handler(False)

    def _message(self, client, userdata, msg):
        if self.handler:
            try:
                self.handler(msg.topic, msg.payload)
            except Exception:
                logging.exception("%s failed to handle topic %s", self.name, msg.topic)

    def start(self, timeout=5):
        self.client.connect(HOST, PORT, keepalive=20)
        self.client.loop_start()
        if not self.ready.wait(timeout):
            self.close()
            raise ConnectionError(f"No MQTT connection to {HOST}:{PORT}")

    def publish(self, topic, payload, retain=False):
        if not self.ready.is_set():
            raise ConnectionError("MQTT client is disconnected or waiting for subscriptions")
        result = self.client.publish(topic, encode(payload), qos=1, retain=retain)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            raise ConnectionError(f"MQTT publish failed: {result.rc}")
        return result

    def close(self):
        self.client.disconnect()
        self.client.loop_stop()
