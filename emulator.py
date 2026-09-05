"""Run one independent device: dht, input, relay, meter or motion."""
import argparse
import sys
from PyQt5.QtWidgets import QApplication
from homeguard.devices import DEVICE_CLASSES

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("device",choices=DEVICE_CLASSES)
    args=parser.parse_args()
    app=QApplication(sys.argv)
    window=DEVICE_CLASSES[args.device]()
    window.setWindowTitle("HomeGuard emulator: "+args.device)
    window.show()
    result=app.exec_()
    window.close_device()
    sys.exit(result)
