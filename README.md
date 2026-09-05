# HomeGuard

A local IoT course project by Ron and Itzhak. Python software devices communicate through a real MQTT broker. A data manager validates and stores measurements in SQLite, evaluates temperature thresholds, sends relay commands and publishes Info/Warning/Alarm events. A PyQt5 dashboard displays live values, persisted history, events and relay acknowledgements.

## Run

Use Python 3.12 on Windows (the platform used for validation).

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run_demo.py
```

The launcher starts a local broker, a separate data manager process and a GUI containing DHT, Button/Knob and Relay emulators. Extra meter and motion producers also run. Each emulator owns its own MQTT client. Closing the dashboard stops the child processes created by the launcher. No database download, account, paid service or cloud credential is required.

Use `python` instead of `.venv\Scripts\python` below if you have already activated the virtual environment.

## Try the two main flows

1. Change DHT temperature from 24 to 32 C: the manager stores readings, publishes WARNING and requests the relay ON. Change to 37 C for ALARM. Return to 25 C for INFO and relay OFF. The warning threshold defaults to 30 C, alarm to 35 C and automatic reset to 28 C. The two-degree reset gap avoids repeated switching near the warning threshold.
2. Click **Toggle relay (manual)**. A real input message reaches the manager, which switches to MANUAL mode and publishes a relay command. The relay acknowledges its state. Sensor updates do not cancel manual control. Click **Restore automatic control** to resume threshold decisions. Change the knob to 24 C and click **Send threshold**: the last temperature is reassessed immediately. The alarm threshold is always five degrees above the warning threshold.

The GUI has three lower tabs: events, received MQTT traffic and the executing threshold function from `homeguard/service.py`. The graph reads the persisted SQLite measurements. The lower status line shows database counts and age of the last sensor message.

## Components

| Module | Responsibility |
| --- | --- |
| `homeguard/devices.py` | DHT, Button/Knob, Relay, meter and motion emulators |
| `homeguard/broker.py` | Standard aMQTT broker bound to loopback |
| `homeguard/mqtt.py` | Paho MQTT 3.1.1 clients with QoS 1 and resubscription |
| `homeguard/protocol.py` | Message schema, IDs, timestamps and value validation |
| `homeguard/storage.py` | SQLite initialization, transactional storage and history |
| `homeguard/service.py` | Data manager, events, control modes, thresholds and commands |
| `homeguard/dashboard.py` | PyQt5 GUI and pyqtgraph history |
| `homeguard/recording.py` | Capture of actual Qt frames during a controlled live demo |

The repository's original code is retained in `legacy/` for comparison and is not launched. See `CHANGELOG.md` for changes from the baseline.

## MQTT topics

All topics start with `pr/HomeGuard/` by default.

| Topic suffix | Publisher | Subscriber |
| --- | --- | --- |
| `telemetry/dht` | DHT | Manager, GUI |
| `telemetry/meter` | Meter | Manager, GUI |
| `telemetry/motion` | Motion | Manager, GUI |
| `input/button`, `input/knob` | Input emulator | Manager, GUI |
| `command/relay` | Manager | Relay, GUI |
| `state/relay` | Relay | Manager, GUI |
| `state/manager`, `events` | Manager | GUI |

Each JSON payload carries `version`, unique `id`, UTC `timestamp`, `device`, `kind` and type-specific fields. QoS 1 can redeliver a message; the database primary key prevents processing the same input twice. This does not claim guaranteed delivery across process restarts or an offline write queue.

## SQLite

The file `data/homeguard.db` is created automatically. Tables: `messages` (validated original messages), `data` (individual measurements), `iot_devices` (last device state), and `events` (timestamp/severity/text). Timestamps are UTC. The database and generated logs are ignored by Git.

## Separate processes and configuration

```powershell
python -m homeguard.broker
python manager.py
python emulator.py dht
python emulator.py input
python emulator.py relay
python gui.py
```

Run each command in a separate terminal. The standalone GUI does not start devices or services.

Supported environment variables:

- `HOMEGUARD_HOST`: broker address, default `127.0.0.1`.
- `HOMEGUARD_PORT`: broker port, default `1883`.
- `HOMEGUARD_TOPIC`: topic prefix, default `pr/HomeGuard`.
- `HOMEGUARD_DB`: absolute or relative SQLite path.

`python run_demo.py --external-broker` uses the configured existing broker. The launcher refuses to replace a process already listening on its chosen port. Use another port when needed. For example, `$env:HOMEGUARD_PORT='18886'`.

## Tests and repeatable demo

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
python run_demo.py --record recordings/HomeGuard_Demo.mp4
```

Optional `--offscreen` renders the actual Qt application without opening a desktop window. On Windows the recorder registers installed fonts explicitly. The MP4 is recorded from the running application, not assembled from fake screenshots. The scenario changes the real input widgets; messages traverse a real local MQTT broker and are stored by a separate manager process. No microphone, webcam or unrelated desktop content is captured.

For a clean measurement count in each recording, set `HOMEGUARD_DB` to a new file. Existing database history is preserved by default.

## Validation of the supplied recording

- 25 automated tests passed, including a full GUI/device/manager/SQLite run through a real broker, invalid input handling and recovery after restarting the broker.
- 76.1 second H.264 MP4, 1600 x 900, 10 frames/second.
- All three event levels and both relay states were observed.
- Button and knob messages were received.
- The recorded run persisted 261 measurements and 18 events for five devices; the GUI observed 319 MQTT messages.
- The run used local port 18886. Counts depend on runtime and are not performance guarantees.

## Limits and remaining submission work

Software emulators only. No implemented CO2/air-pollution measurement, physical hardware calibration, login/registration, mobile app, cloud DB or automatic room-temperature physics. Turning the relay on changes its state; it does not itself lower the simulated DHT input. The extra sensitivity value is a simulated legacy quantity, not an acoustic or health metric.

The default local broker has no TLS or user authentication and listens only on loopback. This demo is not a production deployment and has no claimed GDPR compliance, 99.9% availability or guaranteed latency.

Record a 10–12 minute explanation by Ron and Itzhak and insert its link into the 12-slide presentation.

The test suite uses an available local port and a temporary database. Device windows show connection loss, and input commands attempted while disconnected are not applied later. After reconnection, subscriptions are acknowledged before clients report readiness, and fresh sensor readings resume automatic control.

## Sources

- Course reference: https://github.com/yuryyu/SmartHome
- MQTT client: https://eclipse.dev/paho/files/paho.mqtt.python/html/
- Qt: https://doc.qt.io/qt-5/qtwidgets-index.html
- SQLite: https://www.sqlite.org/docs.html
- Broker: https://amqtt.readthedocs.io/

See `LICENSE` for the repository license.
