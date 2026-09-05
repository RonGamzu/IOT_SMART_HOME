"""Start the HomeGuard data manager (requires a running MQTT broker)."""
import logging
import time
from homeguard.service import DataManager

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,format="%(asctime)s %(message)s")
    manager=DataManager()
    manager.start()
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        manager.close()
