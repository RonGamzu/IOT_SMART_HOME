"""A standard aMQTT broker bound to loopback for the local course demo."""
import asyncio
import logging
from amqtt.broker import Broker
from .config import PORT

async def serve():
    broker=Broker({"listeners":{"default":{"type":"tcp","bind":f"127.0.0.1:{PORT}"}},
        "plugins":{"amqtt.plugins.authentication.AnonymousAuthPlugin":{"allow_anonymous":True}}})
    await broker.start()
    print(f"Local MQTT broker ready on 127.0.0.1:{PORT}",flush=True)
    try:
        await asyncio.Event().wait()
    finally:
        await broker.shutdown()

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass
