"""Capture actual Qt frames while the real MQTT system executes a demo scenario.

No desktop, unrelated application, microphone or camera is captured.
The controls below exercise the same input widgets a person can use.
"""
import json
import time
from pathlib import Path
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QImage
import imageio_ffmpeg

class Recorder:
    def __init__(self, window, output, seconds=76):
        self.window=window
        self.output=Path(output)
        self.output.parent.mkdir(parents=True,exist_ok=True)
        self.seconds=seconds
        self.fps=10
        self.frame=0
        self.started=time.monotonic()
        self.writer=imageio_ffmpeg.write_frames(str(self.output),(1600,900),fps=self.fps,
            codec="libx264",pix_fmt_in="rgba",pix_fmt_out="yuv420p",quality=8,
            output_params=["-movflags","+faststart","-preset","veryfast"],macro_block_size=1)
        self.writer.send(None)
        window.setFixedSize(1600,900)
        self.timer=QTimer(window)
        self.timer.timeout.connect(self.capture)
        self.timer.start(100)
        self.scenes=[
            (0,"1. NORMAL | DHT measurements arrive through MQTT and enter SQLite",lambda:None),
            (10,"2. WARNING | 32 C crosses the 30 C threshold; fan relay turns ON",lambda:window.dht.temp.setValue(32)),
            (22,"3. ALARM | 37 C crosses the 35 C alarm threshold",lambda:window.dht.temp.setValue(37)),
            (34,"4. RECOVERY | 25 C is below the 28 C reset threshold",lambda:window.dht.temp.setValue(25)),
            (43,"5. BUTTON | Manual ON command and relay acknowledgement",lambda:window.inputs.toggle.click()),
            (49,"6. AUTO | Automatic control restored; relay turns OFF",lambda:window.inputs.automatic.click()),
            (55,"7. KNOB | Lower the warning threshold to 24 C",self.lower_threshold),
            (62,"8. LIVE NETWORK | Inspect real MQTT messages and acknowledgements",lambda:window.tabs.setCurrentIndex(1)),
            (67,"9. RUNNING CODE | DataManager.evaluate controls the thresholds and relay",lambda:window.tabs.setCurrentIndex(2)),
            (72,"10. DATABASE | Measurements and events persisted by the manager",lambda:window.tabs.setCurrentIndex(0)),
        ]
        self.next_scene=0
        self.saved=set()

    def lower_threshold(self):
        self.window.inputs.knob.setValue(24)
        self.window.inputs.apply.click()

    def capture(self):
        elapsed=time.monotonic()-self.started
        while self.next_scene<len(self.scenes) and elapsed>=self.scenes[self.next_scene][0]:
            _,label,action=self.scenes[self.next_scene]
            self.window.scene.setText(label)
            action()
            self.next_scene+=1
        pix=self.window.grab()
        for mark,label in [(8,"normal"),(19,"warning"),(30,"alarm"),(40,"recovery"),(47,"manual"),(65,"trace"),(70,"code")]:
            if elapsed>=mark and label not in self.saved:
                pix.save(str(self.output.parent/f"demo-{label}.png"))
                self.saved.add(label)
        im=pix.toImage().convertToFormat(QImage.Format_RGBA8888)
        pointer=im.bits()
        pointer.setsize(im.byteCount())
        # Repeat a captured frame if rendering missed a timer tick; keep real time.
        frame_bytes=bytes(pointer)
        frames_due=max(1,round(elapsed*self.fps)-self.frame)
        for _ in range(frames_due):
            self.writer.send(frame_bytes)
            self.frame+=1
        if elapsed>=self.seconds:
            self.finish()

    def finish(self):
        self.timer.stop()
        self.writer.close()
        w=self.window
        evidence={"video":self.output.name,"frames":self.frame,"fps":self.fps,
            "duration_seconds":self.frame/self.fps,"wall_seconds":round(time.monotonic()-self.started,2),
            "captured":"Actual Qt application frames during live MQTT execution",
            "levels":sorted(w.observed_levels),"relay_states":sorted(w.observed_relays),
            "input_devices":sorted(w.observed_commands),"database":w.store.counts(),
            "mqtt_packets":w.packet_count,"events":w.store.events(100)}
        evidence["passed"]=(set(evidence["levels"])=={"INFO","WARNING","ALARM"}
            and evidence["relay_states"]==[False,True]
            and evidence["input_devices"]==["button","knob"]
            and evidence["database"]["data"]>50)
        self.output.with_suffix(".evidence.json").write_text(json.dumps(evidence,indent=2),encoding="utf-8")
        print(json.dumps({k:v for k,v in evidence.items() if k!="events"}),flush=True)
        from PyQt5.QtWidgets import QApplication
        w.close()
        QApplication.instance().quit()
