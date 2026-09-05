"""Data manager: validate, store, evaluate thresholds, publish events/commands."""
import json
import logging
from .config import topic, WARN_TEMP, ALARM_TEMP, HYSTERESIS
from .protocol import decode, message, number
from .storage import Store
from .mqtt import Bus

class DataManager:
    def __init__(self, store=None, publisher=None):
        self.store = store or Store()
        self.warning = WARN_TEMP
        self.alarm = ALARM_TEMP
        self.severity = "INFO"
        self.temperature = None
        self.mode = "AUTO"
        self.relay_actual = False
        self.relay_target = None
        self.publish = publisher
        self.bus = None

    def start(self):
        self.bus = Bus("manager", [topic("telemetry/#"),topic("input/#"),topic("state/relay")], self.receive)
        self.publish = self.bus.publish
        self.bus.start()
        self.emit("INFO", "Manager started; SQLite ready; automatic control enabled")

    def emit(self, severity, text):
        event_id = self.store.event(severity, "manager", text)
        logging.info("%s | %s", severity, text)
        self.publish(topic("events"), message("manager","event",severity=severity,text=text,event_id=event_id))

    def status(self):
        self.publish(topic("state/manager"), message("manager","status",severity=self.severity,
            warning=self.warning,alarm=self.alarm,temperature=self.temperature,mode=self.mode,
            relay_target=self.relay_target,relay_actual=self.relay_actual), retain=True)

    def relay(self, state, reason, force=False):
        if state == self.relay_target and not force:
            return
        self.publish(topic("command/relay"),message("manager","command",state=state,reason=reason))
        self.relay_target = state
        self.emit("INFO",f"Relay requested {'ON' if state else 'OFF'}: {reason}")

    def evaluate(self):
        if self.temperature is None:
            return
        t = self.temperature
        level = "ALARM" if t >= self.alarm else "WARNING" if t >= self.warning else "INFO"
        if level != self.severity:
            self.severity = level
            self.emit(level,f"Temperature {t:.1f} C; warning {self.warning:.0f} C; alarm {self.alarm:.0f} C")
        if self.mode == "AUTO":
            if t >= self.warning:
                self.relay(True, "temperature above warning threshold")
            elif t <= self.warning-HYSTERESIS:
                self.relay(False, "temperature below reset threshold")
        self.status()

    def receive(self, name, raw):
        try:
            p = decode(raw)
            kind = p["kind"]
            metrics = []
            if name == topic("telemetry/dht") and kind == "dht":
                metrics = [("temperature",number(p.get("temperature"),-40,100),"C"),
                           ("humidity",number(p.get("humidity"),0,100),"%")]
            elif name == topic("telemetry/meter") and kind == "meter":
                metrics = [("electricity",number(p.get("electricity"),0,100),"kWh/sample"),
                           ("sensitivity",number(p.get("sensitivity"),0,1),"simulated")]
            elif name == topic("telemetry/motion") and kind == "motion":
                metrics = [("distance",number(p.get("distance"),0,1000),"cm")]
            elif name == topic("input/button") and kind == "button":
                if p.get("action") not in ("toggle", "auto"):
                    raise ValueError("Unknown button action")
            elif name == topic("input/knob") and kind == "knob":
                number(p.get("warning"),22,36)
            elif name == topic("state/relay") and kind == "relay":
                if not isinstance(p.get("state"),bool):
                    raise ValueError("Relay state must be boolean")
            else:
                raise ValueError("Unexpected topic or message kind")
            if not self.store.record(name,p,metrics):
                return
            if kind == "dht":
                self.temperature = metrics[0][1]
                self.evaluate()
            elif kind == "button":
                if p["action"] == "auto":
                    self.mode = "AUTO"
                    self.emit("INFO","Automatic relay control restored")
                    self.evaluate()
                else:
                    self.mode = "MANUAL"
                    # Target is authoritative for consecutive clicks before the acknowledgement arrives.
                    base = self.relay_actual if self.relay_target is None else self.relay_target
                    self.relay(not base,"manual button")
                self.status()
            elif kind == "knob":
                self.warning = float(p["warning"])
                self.alarm = self.warning+5
                self.emit("INFO",f"Knob changed warning to {self.warning:.0f} C and alarm to {self.alarm:.0f} C")
                self.evaluate()
                self.status()
            elif kind == "relay":
                changed = self.relay_actual != p["state"]
                self.relay_actual = p["state"]
                if changed:
                    self.emit("INFO",f"Relay acknowledged {'ON' if self.relay_actual else 'OFF'}")
                self.status()
                # A restarted device reports OFF and receives a fresh command if needed.
                if self.relay_target is not None and self.relay_actual != self.relay_target:
                    self.relay(self.relay_target,"resynchronize relay",force=True)
            elif kind == "meter":
                # Meter is retained from the original project as an extra producer.
                pass
        except (ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
            self.emit("WARNING",f"Rejected invalid message on {name}: {exc}")

    def close(self):
        if self.bus:
            self.bus.close()
