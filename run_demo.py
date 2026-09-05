"""Start the local broker, manager, GUI and real software devices."""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent

def wait_for_broker(host,port,timeout=10):
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        try:
            with socket.create_connection((host,port),timeout=.2):
                return
        except OSError:
            time.sleep(.1)
    raise ConnectionError(f"MQTT broker did not start on {host}:{port}")

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record",type=Path,help="Capture a 76 second real demo to MP4")
    parser.add_argument("--offscreen",action="store_true",help="Render the actual Qt GUI without a desktop window")
    parser.add_argument("--external-broker",action="store_true",help="Use configured broker instead of starting a local one")
    args=parser.parse_args()
    if args.offscreen:
        os.environ["QT_QPA_PLATFORM"]="offscreen"
    from homeguard.config import HOST,PORT,DB_PATH
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    processes=[]
    files=[]
    try:
        def launch(script,name):
            log=open(DB_PATH.parent/f"{name}.log","w",encoding="utf-8")
            files.append(log)
            flags=subprocess.CREATE_NO_WINDOW if os.name=="nt" else 0
            process=subprocess.Popen([sys.executable,"-u",*script],cwd=ROOT,stdout=log,stderr=log,creationflags=flags)
            processes.append(process)
            return process
        if not args.external_broker:
            with socket.socket() as probe:
                if probe.connect_ex((HOST,PORT))==0:
                    raise RuntimeError(f"Port {PORT} is already in use; choose HOMEGUARD_PORT or --external-broker")
            launch(["-m","homeguard.broker"],"broker")
        wait_for_broker(HOST,PORT)
        # Wait for manager's startup event, not a guessed fixed delay.
        from homeguard.storage import Store
        store=Store()
        baseline=store.counts()["events"]
        manager=launch(["manager.py"],"manager")
        deadline=time.monotonic()+10
        while store.counts()["events"]<=baseline:
            if manager.poll() is not None or time.monotonic()>deadline:
                raise RuntimeError("Manager failed to start; inspect data/manager.log")
            time.sleep(.1)
        from PyQt5.QtWidgets import QApplication
        from homeguard.dashboard import Dashboard
        from homeguard.devices import MeterDevice,MotionDevice
        app=QApplication(sys.argv)
        app.setStyle("Fusion")
        if args.offscreen and os.name == "nt":
            # Qt's offscreen Windows backend starts with an empty font database.
            from PyQt5.QtGui import QFontDatabase,QFont
            fonts=Path(os.environ.get("WINDIR","C:/Windows"))/"Fonts"
            for filename in ("arial.ttf","arialbd.ttf","segoeui.ttf","segoeuib.ttf","consola.ttf"):
                QFontDatabase.addApplicationFont(str(fonts/filename))
            app.setFont(QFont("Segoe UI",10))
        window=Dashboard()
        # Additional original producer types run as live MQTT clients too.
        window.devices.extend([MeterDevice(),MotionDevice()])
        window.show()
        if args.record:
            from homeguard.recording import Recorder
            window.recorder=Recorder(window,args.record)
        result=app.exec_()
        if args.record:
            import json
            evidence=json.loads(args.record.with_suffix(".evidence.json").read_text())
            if not evidence["passed"]:
                raise RuntimeError("Recording validation failed; inspect evidence JSON")
        return result
    finally:
        for p in reversed(processes):
            if p.poll() is None:
                p.terminate()
                try:p.wait(timeout=5)
                except subprocess.TimeoutExpired:p.kill()
        for f in files:f.close()

if __name__=="__main__":
    raise SystemExit(main())
