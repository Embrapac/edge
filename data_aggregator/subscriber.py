import asyncio
import paho.mqtt.client as mqtt
import json

from config import Config
from shared.logger import get_struct_logger

MQTT_DEFAULT_PORT = 1883

logger = get_struct_logger(__name__)

class PubSubSubscriber:
    def __init__(self, broker_url, aggregator):
        self.broker_url = broker_url
        self.aggregator = aggregator
        self.client = None
        self.loop = None

    def on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode())
            topic = message.topic
            logger.info(f"Received MQTT message on topic '{topic}': {payload}")
            # Schedule async method in the event loop from another thread
            if self.loop:
                normalized_event = self._normalize_event(topic, payload)
                if normalized_event is None:
                    logger.warning(f"Received message on unhandled topic '{topic}', ignoring.")
                    return
                asyncio.run_coroutine_threadsafe(self.aggregator.process_pubsub_event(normalized_event), self.loop)
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _normalize_event(self, topic, payload):
        if not isinstance(payload, dict):
            logger.warning(f"Ignoring MQTT payload with unexpected format on topic '{topic}': {payload}")
            return None

        if topic == Config.MQTT_TOPIC_CBELT_STATUS:
            command = payload.get("command") or payload.get("comando")
            return {
                "operation": "control_cbelt",
                "parameters": {
                    **payload,
                    "command": command,
                },
            }

        return None

    async def listen(self):
        # Parse broker URL (assuming format mqtt://host:port)
        if self.broker_url.startswith("mqtt://"):
            host_port = self.broker_url[7:].split(":")
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else MQTT_DEFAULT_PORT
        else:
            host = self.broker_url
            port = MQTT_DEFAULT_PORT

        self.client = mqtt.Client()
        self.client.on_message = self.on_message
        self.client.connect(host, port)
        self.client.subscribe(Config.MQTT_TOPIC_CBELT_STATUS)
        self.loop = asyncio.get_event_loop()
        self.client.loop_start()

        # Keep running
        while True:
            await asyncio.sleep(1)

class PubSubPublisher:
    def __init__(self, host, port=MQTT_DEFAULT_PORT):
        self.broker_url = f"mqtt://{host}:{port}"
        self.host = host
        self.port = port
        self.client = mqtt.Client()
        self.loop = asyncio.get_event_loop()

    def publish(self, topic, payload):
        if self.client:
            logger.debug(f"Connecting to MQTT broker at {self.host}:{self.port} ...")
            self.client.connect(self.host, self.port)
            logger.info(f"Publishing to {topic} at {self.host}:{self.port} with payload: {payload}")
            self.client.publish(topic, payload)
