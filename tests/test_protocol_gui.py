import json
from types import SimpleNamespace
import pytest
from homeguard.protocol import message, decode, encode
from homeguard.config import topic
from homeguard.storage import Store
from homeguard.mqtt import Bus


@pytest.mark.parametrize("change", [
    {"timestamp": "not-a-date"}, {"timestamp": "2026-09-06T12:00:00"},
    {"version": True}, {"temperature": None}, {"humidity": "48"},
    {"temperature": float("inf")}, {"kind": "unknown"},
])
def test_invalid_packet_is_rejected(change):
    packet = message("DHT-1", "dht", temperature=24, humidity=48)
    packet.update(change)
    with pytest.raises(ValueError):
        decode(json.dumps(packet))


def test_timestamp_is_normalized_to_utc():
    packet = message("DHT-1", "dht", temperature=24, humidity=48)
    packet["timestamp"] = "2026-09-06T12:00:00+03:00"
    assert decode(encode(packet))["timestamp"] == "2026-09-06T09:00:00.000+00:00"


class OfflineBus:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass

    def close(self):
        pass

    def publish(self, *args, **kwargs):
        raise ConnectionError("broker disconnected")


def test_gui_survives_invalid_packets_and_accepts_next_reading(qt_app, monkeypatch, tmp_path):
    from homeguard import dashboard
    monkeypatch.setattr(dashboard, "Bus", OfflineBus)
    monkeypatch.setattr(dashboard, "Store", lambda: Store(tmp_path / "gui.db"))
    window = dashboard.Dashboard(include_devices=False)
    try:
        for packet in [message("bad", "dht", temperature="bad", humidity=48),
                       message("bad", "button", action="toggle"),
                       message("bad", "status", severity="ALARM")]:
            window.receive(topic("telemetry/dht"), encode(packet).encode())
        assert window.temp_label.text() == "-- C"
        assert window.packet_count == 0
        window.receive(topic("telemetry/dht"), encode(message("DHT-1", "dht", temperature=25, humidity=50)).encode())
        assert window.temp_label.text() == "25.0 C"
        assert window.hum_label.text() == "50.0 %"
    finally:
        window.close()


def test_device_handles_publish_failure_without_raising(qt_app, monkeypatch):
    from homeguard import devices
    monkeypatch.setattr(devices, "Bus", OfflineBus)
    device = devices.DHTDevice()
    try:
        device.sample()
        assert "message not sent" in device.bus_label.text()
        assert not device.send("telemetry/dht", "dht", temperature=24, humidity=48)
    finally:
        device.close_device()
        device.close()


def test_mqtt_waits_for_all_subscription_acknowledgements():
    status = []
    bus = Bus("test", ["first", "second"], on_status=status.append)
    ids = iter((10, 11))
    client = SimpleNamespace(subscribe=lambda *a, **k: (0, next(ids)))
    ok = SimpleNamespace(is_failure=False)
    bus._connect(client, None, None, ok, None)
    assert not bus.ready.is_set()
    bus._subscribe(client, None, 10, [ok], None)
    assert not bus.ready.is_set()
    bus._subscribe(client, None, 11, [ok], None)
    assert bus.ready.is_set() and status == [True]
    bus._disconnect(client, None, None, ok, None)
    assert not bus.ready.is_set() and status == [True, False]


def test_mqtt_refuses_publish_while_disconnected():
    with pytest.raises(ConnectionError):
        Bus("offline").publish("test", {})
