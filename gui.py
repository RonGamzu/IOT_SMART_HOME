"""Standalone dashboard, for use with separate devices and data manager."""
import sys
from PyQt5.QtWidgets import QApplication
from homeguard.dashboard import Dashboard

if __name__ == "__main__":
    app=QApplication(sys.argv)
    app.setStyle("Fusion")
    window=Dashboard(include_devices=False)
    window.show()
    sys.exit(app.exec_())
