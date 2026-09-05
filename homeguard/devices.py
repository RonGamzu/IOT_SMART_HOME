"""Executable software devices. Each owns a real MQTT client."""
import random
from PyQt5.QtCore import QObject, QTimer, pyqtSignal
from PyQt5.QtWidgets import (QGroupBox,QFormLayout,QDoubleSpinBox,QSpinBox,
                             QPushButton,QLabel,QCheckBox)
from .config import topic
from .protocol import message, decode
from .mqtt import Bus

class Signals(QObject):
    packet = pyqtSignal(str,bytes)
    connection = pyqtSignal(bool)

class Device(QGroupBox):
    def __init__(self, name):
        super().__init__(name)
        self.name = name
        self.form = QFormLayout(self)
        self.signals = Signals()
        self.signals.packet.connect(self.receive)
        self.signals.connection.connect(self.connection_status)
        self.bus_label = QLabel("Connecting to MQTT")
        self.form.addRow(self.bus_label)
        self.bus = Bus(name, [topic("command/relay")] if name == "Relay" else [],
                       lambda t,p:self.signals.packet.emit(t,p),
                       lambda ok:self.signals.connection.emit(ok))
        self.bus.start()

    def connection_status(self, connected):
        self.bus_label.setText("MQTT connected" if connected else "MQTT disconnected; reconnecting")

    def receive(self, name, raw):
        pass

    def send(self, suffix, kind, **fields):
        try:
            self.bus.publish(topic(suffix), message(self.name,kind,**fields))
            return True
        except ConnectionError:
            self.bus_label.setText("MQTT disconnected; message not sent")
            return False

    def close_device(self):
        if hasattr(self,"timer"):
            self.timer.stop()
        self.bus.close()

class DHTDevice(Device):
    def __init__(self):
        super().__init__("DHT-1")
        self.temp = QDoubleSpinBox()
        self.temp.setRange(-10,60)
        self.temp.setValue(24)
        self.temp.setSuffix(" C")
        self.humidity = QDoubleSpinBox()
        self.humidity.setRange(0,100)
        self.humidity.setValue(48)
        self.humidity.setSuffix(" %")
        self.enabled = QCheckBox("Publish every 1 second")
        self.enabled.setChecked(True)
        self.form.addRow("Temperature",self.temp)
        self.form.addRow("Humidity",self.humidity)
        self.form.addRow(self.enabled)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.sample)
        self.timer.start(1000)

    def sample(self):
        if self.enabled.isChecked():
            self.send("telemetry/dht","dht",temperature=round(self.temp.value(),1),
                      humidity=round(self.humidity.value(),1))

class InputDevice(Device):
    def __init__(self):
        super().__init__("Button-Knob")
        self.toggle = QPushButton("Toggle relay (manual)")
        self.automatic = QPushButton("Restore automatic control")
        self.knob = QSpinBox()
        self.knob.setRange(22,36)
        self.knob.setValue(30)
        self.knob.setSuffix(" C")
        self.apply = QPushButton("Send threshold")
        self.form.addRow(self.toggle)
        self.form.addRow(self.automatic)
        self.form.addRow("Warning threshold",self.knob)
        self.form.addRow(self.apply)
        self.toggle.clicked.connect(lambda:self.send("input/button","button",action="toggle"))
        self.automatic.clicked.connect(lambda:self.send("input/button","button",action="auto"))
        self.apply.clicked.connect(lambda:self.send("input/knob","knob",warning=self.knob.value()))

class RelayDevice(Device):
    def __init__(self):
        self.state = False
        self.seen = set()
        super().__init__("Relay")
        self.indicator = QLabel("OFF")
        self.indicator.setStyleSheet("font-size:28px;font-weight:bold;color:#607d8b")
        self.reason = QLabel("Waiting for command")
        self.reason.setWordWrap(True)
        self.form.addRow("Fan relay",self.indicator)
        self.form.addRow(self.reason)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.acknowledge)
        self.timer.start(3000)
        QTimer.singleShot(200,self.acknowledge)

    def receive(self,name,raw):
        try:
            p = decode(raw, "command")
            if name != topic("command/relay") or p["kind"] != "command" or not isinstance(p.get("state"),bool):
                return
            if p["id"] in self.seen:
                return
            self.seen.add(p["id"])
            if len(self.seen)>1000:
                self.seen = {p["id"]}
            self.state = p["state"]
            self.indicator.setText("ON" if self.state else "OFF")
            self.indicator.setStyleSheet(f"font-size:28px;font-weight:bold;color:{'#008577' if self.state else '#607d8b'}")
            self.reason.setText(p.get("reason",""))
            self.acknowledge()
        except (ValueError,KeyError):
            return

    def acknowledge(self):
        self.send("state/relay","relay",state=self.state)

class MeterDevice(Device):
    def __init__(self):
        super().__init__("ElecSensitivityMeter")
        self.reading = QLabel()
        self.form.addRow("Additional producer",self.reading)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.sample)
        self.timer.start(2000)

    def sample(self):
        electricity = round(1.6+random.uniform(-.15,.15),2)
        sensitivity = round(.017+random.uniform(-.004,.004),3)
        self.reading.setText(f"{electricity:.2f} kWh/sample / {sensitivity:.3f}")
        self.send("telemetry/meter","meter",electricity=electricity,sensitivity=sensitivity)

class MotionDevice(Device):
    def __init__(self):
        super().__init__("Motion")
        self.distance = QSpinBox()
        self.distance.setRange(0,1000)
        self.distance.setValue(85)
        self.distance.setSuffix(" cm")
        self.form.addRow("Simulated distance",self.distance)
        self.timer = QTimer(self)
        self.timer.timeout.connect(lambda:self.send("telemetry/motion","motion",distance=self.distance.value()))
        self.timer.start(2000)

DEVICE_CLASSES = {"dht":DHTDevice,"input":InputDevice,"relay":RelayDevice,
                  "meter":MeterDevice,"motion":MotionDevice}
