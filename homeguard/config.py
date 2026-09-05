"""Local demo defaults. Override through environment variables before starting."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = os.getenv("HOMEGUARD_HOST", "127.0.0.1")
PORT = int(os.getenv("HOMEGUARD_PORT", "1883"))
PREFIX = os.getenv("HOMEGUARD_TOPIC", "pr/HomeGuard").strip("/")
DB_PATH = Path(os.getenv("HOMEGUARD_DB", str(ROOT / "data" / "homeguard.db")))
WARN_TEMP = 30.0
ALARM_TEMP = 35.0
HYSTERESIS = 2.0
INTERVAL = 1.0

def topic(suffix):
    return f"{PREFIX}/{suffix.strip('/')}"
