"""Qt dashboard. MQTT callbacks cross to the GUI thread through signals."""
import json
from datetime import datetime,timezone
from pathlib import Path
from PyQt5.QtCore import QObject,QTimer,pyqtSignal,Qt
from PyQt5.QtWidgets import (QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,
    QLabel,QGroupBox,QTableWidget,QTableWidgetItem,QPlainTextEdit,QTabWidget,QSplitter)
from PyQt5.QtGui import QColor,QFont
import pyqtgraph as pg
from .config import topic,HOST,PORT
from .protocol import decode
from .storage import Store
from .mqtt import Bus
from .devices import DHTDevice,InputDevice,RelayDevice,MeterDevice,MotionDevice

STYLE = '''
QWidget {font-family:Segoe UI;font-size:14px;color:#173a43;background:#f4f7f6;}
QMainWindow {background:#f4f7f6;}
QGroupBox {font-weight:600;border:1px solid #c7d8d3;border-radius:7px;margin-top:15px;padding:12px 8px 8px;}
QGroupBox::title {subcontrol-origin:margin;left:10px;padding:0 5px;}
QPushButton {background:#126c62;color:white;border:0;border-radius:4px;padding:8px;}
QPushButton:pressed {background:#0b4d46;}
QDoubleSpinBox,QSpinBox {background:white;padding:5px;min-height:23px;}
QTableWidget {background:white;border:0;gridline-color:#e0e7e4;}
QHeaderView::section {background:#dcebe5;padding:7px;border:0;font-weight:600;}
QTabBar::tab {padding:8px 18px;background:#dcebe5;}
QTabBar::tab:selected {background:#126c62;color:white;}
'''

class GuiSignals(QObject):
    packet = pyqtSignal(str,bytes)
    connection = pyqtSignal(bool)

class Dashboard(QMainWindow):
    def __init__(self, include_devices=True):
        super().__init__()
        self.setWindowTitle("HomeGuard | Running IoT system")
        self.resize(1600,900)
        self.setStyleSheet(STYLE)
        self.store = Store()
        self.signals = GuiSignals()
        self.signals.packet.connect(self.receive)
        self.signals.connection.connect(self.connection_status)
        self.samples = []
        self.times = []
        self.packet_count = 0
        self.last_sensor = None
        self.devices = []
        self.observed_levels = set()
        self.observed_relays = set()
        self.observed_commands = set()
        self.event_ids = set()
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22,16,22,16)
        title_row = QHBoxLayout()
        title = QLabel("HomeGuard")
        title.setStyleSheet("font-size:34px;font-weight:700;color:#125c53")
        self.connection_label = QLabel(f"Connecting to MQTT {HOST}:{PORT}")
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(self.connection_label)
        layout.addLayout(title_row)
        self.scene = QLabel("Live monitoring | software device emulators")
        self.scene.setStyleSheet("font-size:19px;padding:7px 0;color:#576d72")
        layout.addWidget(self.scene)
        body = QHBoxLayout()
        if include_devices:
            device_layout = QVBoxLayout()
            self.dht = DHTDevice()
            self.inputs = InputDevice()
            self.relay = RelayDevice()
            self.devices = [self.dht,self.inputs,self.relay]
            for device in self.devices:
                device.setMinimumWidth(300)
                device.setMaximumWidth(330)
                device_layout.addWidget(device)
            body.addLayout(device_layout,0)
        right = QVBoxLayout()
        metrics = QHBoxLayout()
        self.temp_label = self.add_metric(metrics,"TEMPERATURE","-- C")
        self.hum_label = self.add_metric(metrics,"HUMIDITY","-- %")
        self.level_label = self.add_metric(metrics,"STATUS","Waiting")
        self.relay_label = self.add_metric(metrics,"RELAY ACK","--")
        right.addLayout(metrics)
        self.detail = QLabel("Waiting for sensor and manager messages")
        right.addWidget(self.detail)
        self.graph = pg.PlotWidget(axisItems={"bottom":pg.DateAxisItem(orientation="bottom")})
        self.graph.setBackground("#ffffff")
        self.graph.showGrid(x=True,y=True,alpha=.15)
        self.graph.setLabel("left","Temperature",units="C")
        self.graph.setLabel("bottom","Time")
        self.graph.setYRange(18,42)
        self.curve = self.graph.plot(pen=pg.mkPen("#008577",width=3),symbol="o",symbolSize=4)
        self.warn_line = pg.InfiniteLine(pos=30,angle=0,pen=pg.mkPen("#cf910d",style=Qt.DashLine),label="Warning {value:.0f} C")
        self.alarm_line = pg.InfiniteLine(pos=35,angle=0,pen=pg.mkPen("#c94445",style=Qt.DashLine),label="Alarm {value:.0f} C")
        self.graph.addItem(self.warn_line)
        self.graph.addItem(self.alarm_line)
        right.addWidget(self.graph,3)
        self.tabs = QTabWidget()
        self.table = QTableWidget(0,3)
        self.table.setHorizontalHeaderLabels(["Time","Severity","Event"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0,100)
        self.table.setColumnWidth(1,100)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabs.addTab(self.table,"Info / Warning / Alarm")
        self.trace = QPlainTextEdit()
        self.trace.setReadOnly(True)
        self.trace.setMaximumBlockCount(250)
        self.trace.setStyleSheet("background:#12232b;color:#a4e2ca;font-family:Consolas;font-size:13px")
        self.tabs.addTab(self.trace,"MQTT trace")
        self.code = QPlainTextEdit()
        self.code.setReadOnly(True)
        source = (Path(__file__).parent/"service.py").read_text(encoding="utf-8")
        begin=source.index("    def evaluate(self):")
        end=source.index("    def receive(self,",begin)
        self.code.setPlainText("# Executing module: homeguard/service.py\n"+source[begin:end])
        self.code.setStyleSheet("background:#12232b;color:#a4e2ca;font-family:Consolas;font-size:14px")
        self.tabs.addTab(self.code,"Running code")
        right.addWidget(self.tabs,3)
        body.addLayout(right,1)
        layout.addLayout(body,1)
        self.footer = QLabel()
        layout.addWidget(self.footer)
        self.setCentralWidget(root)
        self.bus = Bus("gui",[topic("#")], lambda t,p:self.signals.packet.emit(t,p),
                       lambda ok:self.signals.connection.emit(ok))
        self.bus.start()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_db)
        self.timer.start(1000)
        self.refresh_db()

    def add_metric(self, layout, name, value):
        col = QVBoxLayout()
        label = QLabel(name)
        label.setStyleSheet("font-size:12px;color:#617b80;font-weight:600")
        number = QLabel(value)
        number.setStyleSheet("font-size:30px;font-weight:650")
        col.addWidget(label)
        col.addWidget(number)
        layout.addLayout(col,1)
        return number

    def connection_status(self,ok):
        self.connection_label.setText(f"MQTT {'connected' if ok else 'disconnected'} | {HOST}:{PORT}")

    def receive(self,name,raw):
        kinds={"telemetry/dht":"dht", "telemetry/meter":"meter", "telemetry/motion":"motion",
               "state/manager":"status", "state/relay":"relay", "events":"event",
               "input/button":"button", "input/knob":"knob", "command/relay":"command"}
        expected=next((kind for suffix,kind in kinds.items() if name==topic(suffix)),None)
        if expected is None:
            return
        try:
            p = decode(raw, expected)
        except ValueError:
            return
        self.packet_count += 1
        # Trace is actual received network traffic, not scripted example output.
        short={k:v for k,v in p.items() if k not in ("version","id","timestamp")}
        self.trace.appendPlainText(f"{datetime.now():%H:%M:%S} {name}\n{json.dumps(short)}")
        if name == topic("telemetry/dht"):
            self.last_sensor = datetime.now(timezone.utc)
            self.temp_label.setText(f"{p['temperature']:.1f} C")
            self.hum_label.setText(f"{p['humidity']:.1f} %")
        elif name == topic("state/manager"):
            level=p["severity"]
            self.observed_levels.add(level)
            self.level_label.setText(level)
            color={"INFO":"#008577","WARNING":"#bc8105","ALARM":"#c83d41"}.get(level,"#566")
            self.level_label.setStyleSheet(f"font-size:30px;font-weight:700;color:{color}")
            self.detail.setText(f"Control: {p['mode']}    |    Warning: {p['warning']:.0f} C    |    Alarm: {p['alarm']:.0f} C    |    Reset: {p['warning']-2:.0f} C")
            self.warn_line.setValue(p["warning"])
            self.alarm_line.setValue(p["alarm"])
        elif name == topic("state/relay"):
            self.observed_relays.add(p["state"])
            self.relay_label.setText("ON" if p["state"] else "OFF")
        elif name in (topic("input/button"),topic("input/knob")):
            self.observed_commands.add(name.rsplit("/",1)[-1])
        elif name == topic("events"):
            self.add_event(p["timestamp"],p["severity"],p["text"],p.get("event_id"))

    def add_event(self,stamp,level,text,event_id):
        if event_id in self.event_ids:
            return
        self.event_ids.add(event_id)
        self.table.insertRow(0)
        for c,value in enumerate((stamp[11:19],level,text)):
            item=QTableWidgetItem(value)
            if c==1:
                item.setForeground(QColor({"INFO":"#008577","WARNING":"#b07900","ALARM":"#c83d41"}.get(level,"#333")))
            self.table.setItem(0,c,item)
        if self.table.rowCount()>100:
            self.table.removeRow(100)

    def refresh_db(self):
        history = self.store.history()
        self.times=[datetime.fromisoformat(r["timestamp"]).timestamp() for r in history]
        self.samples=[r["value"] for r in history]
        self.curve.setData(self.times,self.samples)
        for row in reversed(self.store.events(20)):
            self.add_event(row["timestamp"],row["severity"],row["message"],row["id"])
        c=self.store.counts()
        fresh="No sensor data"
        if self.last_sensor:
            age=(datetime.now(timezone.utc)-self.last_sensor).total_seconds()
            fresh=f"Sensor age {age:.0f}s"+(" (STALE)" if age>5 else "")
        self.footer.setText(f"SQLite: {c['data']} measurements | {c['events']} events | {c['iot_devices']} devices    |    MQTT received: {self.packet_count}    |    {fresh}")

    def closeEvent(self,event):
        self.timer.stop()
        self.bus.close()
        for device in self.devices:
            device.close_device()
        event.accept()
