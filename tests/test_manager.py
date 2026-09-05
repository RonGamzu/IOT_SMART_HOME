import json
import pytest
from homeguard.config import topic
from homeguard.protocol import message,encode,decode
from homeguard.service import DataManager
from homeguard.storage import Store

@pytest.fixture
def system(tmp_path):
    sent=[]
    manager=DataManager(Store(tmp_path/"test.db"),lambda t,p,**kw:sent.append((t,p)))
    return manager,sent

def send(manager,suffix,kind,device="test",**fields):
    p=message(device,kind,**fields)
    manager.receive(topic(suffix),encode(p).encode())
    return p

def test_temperature_warning_alarm_and_recovery(system):
    m,sent=system
    for temp,expected,target in [(24,"INFO",False),(32,"WARNING",True),(37,"ALARM",True),(29,"INFO",True),(27,"INFO",False)]:
        send(m,"telemetry/dht","dht",temperature=temp,humidity=48)
        assert m.severity==expected
        assert m.relay_target is target
    assert m.store.counts()["data"]==10
    assert {e["severity"] for e in m.store.events()}=={"INFO","WARNING","ALARM"}
    commands=[p["state"] for t,p in sent if t==topic("command/relay")]
    assert commands==[False,True,False]  # hysteresis avoids repeated/chattering commands

def test_manual_toggle_is_not_overridden_by_sensor(system):
    m,_=system
    send(m,"telemetry/dht","dht",temperature=24,humidity=50)
    send(m,"input/button","button",action="toggle")
    assert m.mode=="MANUAL" and m.relay_target is True
    send(m,"telemetry/dht","dht",temperature=24,humidity=50)
    assert m.relay_target is True
    send(m,"input/button","button",action="auto")
    assert m.mode=="AUTO" and m.relay_target is False

def test_knob_reassesses_last_reading(system):
    m,_=system
    send(m,"telemetry/dht","dht",temperature=26,humidity=50)
    send(m,"input/knob","knob",warning=24)
    assert (m.warning,m.alarm,m.severity,m.relay_target)==(24,29,"WARNING",True)

def test_duplicate_qos_packet_has_no_duplicate_effect(system):
    m,sent=system
    p=send(m,"input/button","button",action="toggle")
    count=len(sent)
    m.receive(topic("input/button"),encode(p).encode())
    assert len(sent)==count
    assert m.store.counts()["messages"]==1

@pytest.mark.parametrize("fields",[{"temperature":float("nan"),"humidity":50},
    {"temperature":24,"humidity":101},{"temperature":True,"humidity":50},
    {"temperature":"24","humidity":50},{"temperature":24}])
def test_bad_sensor_payload_does_not_crash_or_store_data(system,fields):
    m,_=system
    raw=json.dumps(message("bad","dht",**fields)).encode()
    m.receive(topic("telemetry/dht"),raw)
    assert m.store.counts()["data"]==0
    assert m.store.events()[0]["severity"]=="WARNING"
    send(m,"telemetry/dht","dht",temperature=24,humidity=50)
    assert m.store.counts()["data"]==2

def test_wrong_topic_cannot_trigger_relay(system):
    m,sent=system
    send(m,"telemetry/dht","button",action="toggle")
    assert not [p for t,p in sent if t==topic("command/relay")]

def test_database_survives_new_store_instance(system):
    m,_=system
    send(m,"telemetry/dht","dht",temperature=25.5,humidity=45)
    assert Store(m.store.path).history()[0]["value"]==25.5

def test_relay_restart_is_resynchronized(system):
    m,sent=system
    send(m,"telemetry/dht","dht",temperature=32,humidity=50)
    send(m,"state/relay","relay",state=False)
    assert [p for t,p in sent if t==topic("command/relay")][-1]["state"] is True
