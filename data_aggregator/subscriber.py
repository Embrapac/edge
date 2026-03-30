import asyncio
import paho.mqtt.client as mqtt
import json

from config import Config

MQTT_DEFAULT_PORT = 1883

class PubSubSubscriber:
    def __init__(self, broker_url, aggregator):
        self.broker_url = broker_url
        self.aggregator = aggregator
        self.client = None
        self.loop = None

    def on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode())
            # Schedule async method in the event loop from another thread
            if self.loop:
                asyncio.run_coroutine_threadsafe(self.aggregator.process_pubsub_event(payload), self.loop)
        except Exception as e:
            print(f"Error processing message: {e}")

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
        self.client.subscribe(Config.MQTT_TOPIC_DETECTIONS)
        self.loop = asyncio.get_event_loop()
        self.client.loop_start()

        # Keep running
        while True:
            await asyncio.sleep(1)

    def publish(self, topic, payload):
        if self.client:
            self.client.publish(topic, payload)
