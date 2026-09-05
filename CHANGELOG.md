# HomeGuard revision for the final course submission

Baseline: `452ba8a9fd7b91ccea9e5cfa1e57db86314da8a4` (5 September 2026).
The original source is preserved under `legacy/`.

## Added and corrected

- Added working Button/Knob input and Relay actuator emulators, alongside DHT and the extra meter/motion producers.
- Replaced inconsistent topic concatenation and text splitting with explicit MQTT topics and validated versioned JSON.
- Updated the MQTT client to Paho 2.1 and resubscription on reconnect.
- Added local aMQTT broker startup on loopback; removed startup dependence on unrelated external DNS names.
- Added automatic SQLite schema initialization, per-message transactions, parameterized queries and message deduplication.
- Added temperature warning/alarm/recovery processing, relay commands, state acknowledgements and two-degree hysteresis.
- Added manual/automatic control modes and immediate reassessment after a threshold change.
- Replaced unsafe cross-thread GUI updates with Qt signals; the graph reads the actual SQLite history.
- Replaced the incorrect README technology claims with Python/PyQt5/MQTT/SQLite setup and architecture instructions.
- Added 25 tests for the decision logic, validation, duplicate handling, persistence, GUI error handling and a complete MQTT run with broker restart.
- Validate timestamps, message types and payload fields before updating the GUI or saving measurements.
- Wait for MQTT subscription acknowledgements before reporting a client ready.
- Keep device windows running during connection loss and show when an input message was not sent.
- Added a repeatable 76-second demo recorder that captures the actual Qt window during live MQTT operation.
- Archived the incomplete speech/FFT modules instead of presenting them as implemented features.

## Scope retained

This is a software emulator project. There is no implemented CO2 sensor, login/registration,
cloud database, mobile app, calibrated hardware, guaranteed availability or TLS in the local demo.
The broker binds only to `127.0.0.1`. Deployment outside the local machine requires separate security work.

## Submission artifacts

The accompanying presentation contains 12 slides and the embedded demo on slide 10.
The previous 19-slide PDF described several unimplemented features and was rewritten accordingly.
The students' 10–12 minute presentation recording is still pending and must be linked before submission.
