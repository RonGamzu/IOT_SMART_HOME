"""Versioned JSON payloads; transport is MQTT 3.1.1 with QoS 1."""
import json
import math
import uuid
from datetime import datetime, timezone

def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")

def message(device, kind, **fields):
    return dict(version=1, id=uuid.uuid4().hex, timestamp=timestamp(),
                device=device, kind=kind, **fields)

def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False)

def decode(raw, expected_kind=None):
    if len(raw) > 65536:
        raise ValueError("Payload too large")
    value = json.loads(raw)
    if not isinstance(value, dict) or type(value.get("version")) is not int or value["version"] != 1:
        raise ValueError("Expected a version 1 JSON object")
    for key in ("id", "device", "kind", "timestamp"):
        if not isinstance(value.get(key), str) or not value[key] or len(value[key]) > 128:
            raise ValueError(f"Missing or invalid {key}")
    stamp = datetime.fromisoformat(value["timestamp"])
    if stamp.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")
    value["timestamp"] = stamp.astimezone(timezone.utc).isoformat(timespec="milliseconds")
    kind = value["kind"]
    if expected_kind is not None and kind != expected_kind:
        raise ValueError("Message kind does not match its topic")
    if kind == "dht":
        number(value.get("temperature"), -40, 100)
        number(value.get("humidity"), 0, 100)
    elif kind == "meter":
        number(value.get("electricity"), 0, 100)
        number(value.get("sensitivity"), 0, 1)
    elif kind == "motion":
        number(value.get("distance"), 0, 1000)
    elif kind == "button":
        if value.get("action") not in ("toggle", "auto"):
            raise ValueError("Unknown button action")
    elif kind == "knob":
        number(value.get("warning"), 22, 36)
    elif kind in ("relay", "command"):
        if not isinstance(value.get("state"), bool):
            raise ValueError("Relay state must be boolean")
        if kind == "command" and not isinstance(value.get("reason", ""), str):
            raise ValueError("Command reason must be text")
    elif kind in ("status", "event"):
        if value.get("severity") not in ("INFO", "WARNING", "ALARM"):
            raise ValueError("Invalid severity")
        if kind == "status":
            number(value.get("warning"), 22, 36)
            number(value.get("alarm"), 27, 41)
            if value.get("temperature") is not None:
                number(value["temperature"], -40, 100)
            if value.get("mode") not in ("AUTO", "MANUAL"):
                raise ValueError("Invalid control mode")
            if not isinstance(value.get("relay_actual"), bool):
                raise ValueError("Invalid actual relay state")
            if value.get("relay_target") is not None and not isinstance(value["relay_target"], bool):
                raise ValueError("Invalid target relay state")
        elif not isinstance(value.get("text"), str) or type(value.get("event_id")) is not int:
            raise ValueError("Invalid event text or ID")
    else:
        raise ValueError("Unknown message kind")
    return value

def number(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Expected numeric measurement")
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"Measurement outside [{low}, {high}]")
    return float(value)
