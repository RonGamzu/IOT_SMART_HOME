"""Exercise the GUI, devices, manager and SQLite through a real local broker."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from homeguard import mqtt, dashboard
from homeguard.protocol import message, encode
from homeguard.config import topic
from homeguard.service import DataManager
from homeguard.storage import Store


def test_complete_system_and_broker_reconnect(qt_app, monkeypatch, tmp_path):
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    monkeypatch.setattr(mqtt, "PORT", port)
    monkeypatch.setattr(dashboard, "PORT", port)
    db_path = tmp_path / "system.db"
    monkeypatch.setattr(dashboard, "Store", lambda: Store(db_path))
    env = {**os.environ, "HOMEGUARD_PORT": str(port)}
    root = Path(__file__).resolve().parents[1]
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    broker = None
    manager = None
    window = None

    def wait_for(condition, timeout=12):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            qt_app.processEvents()
            if condition():
                return
            time.sleep(.02)
        raise AssertionError("Timed out waiting for MQTT system state")

    def listening():
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=.1):
                return True
        except OSError:
            return False

    def start_broker(log):
        proc = subprocess.Popen([sys.executable, "-m", "homeguard.broker"], cwd=root,
                                env=env, stdout=log, stderr=log, creationflags=flags)
        wait_for(listening)
        return proc

    with (tmp_path / "broker.log").open("w") as log:
        try:
            broker = start_broker(log)
            manager = DataManager(Store(db_path))
            manager.start()
            window = dashboard.Dashboard()
            window.show()
            wait_for(lambda: window.temp_label.text() == "24.0 C" and manager.relay_target is False)
            for temperature, level, relay in [(32, "WARNING", True), (37, "ALARM", True), (25, "INFO", False)]:
                window.dht.temp.setValue(temperature)
                window.dht.sample()
                wait_for(lambda: window.level_label.text() == level and window.relay.state is relay
                         and manager.relay_actual is relay)

            window.inputs.toggle.click()
            wait_for(lambda: manager.mode == "MANUAL" and window.relay.state)
            window.dht.sample()
            wait_for(lambda: manager.relay_actual)
            window.inputs.automatic.click()
            wait_for(lambda: manager.mode == "AUTO" and not window.relay.state)
            window.inputs.knob.setValue(24)
            window.inputs.apply.click()
            wait_for(lambda: manager.warning == 24 and window.level_label.text() == "WARNING" and window.relay.state)

            # A bad payload must not terminate Qt or become a stored measurement.
            previous = manager.store.counts()["events"]
            window.bus.client.publish(topic("telemetry/dht"), encode(message("bad", "dht", temperature="bad", humidity=50)), qos=1)
            wait_for(lambda: manager.store.counts()["events"] > previous)
            assert any("Rejected invalid" in e["message"] for e in manager.store.events())

            broker.terminate()
            broker.wait(timeout=5)
            wait_for(lambda: not window.dht.bus.ready.is_set() and not manager.bus.ready.is_set())
            window.dht.sample()
            assert "message not sent" in window.dht.bus_label.text()
            assert not window.inputs.send("input/button", "button", action="toggle")

            broker = start_broker(log)
            wait_for(lambda: manager.bus.ready.is_set() and window.bus.ready.is_set()
                     and all(device.bus.ready.is_set() for device in window.devices))
            window.dht.temp.setValue(20)
            window.dht.sample()
            wait_for(lambda: window.temp_label.text() == "20.0 C" and manager.severity == "INFO"
                     and manager.relay_actual is False and window.relay.state is False)
            assert manager.mode == "AUTO"
            assert {e["severity"] for e in manager.store.events()} == {"INFO", "WARNING", "ALARM"}
            assert Store(db_path).counts()["data"] >= 8
            window.refresh_db()
            assert window.samples[-1] == 20
        finally:
            if window is not None:
                window.close()
            if manager is not None:
                manager.close()
            if broker is not None and broker.poll() is None:
                broker.terminate()
                broker.wait(timeout=5)
