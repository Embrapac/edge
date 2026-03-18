import asyncio
import paho.mqtt.client as mqtt
import json

class PubSubSubscriber:
    def __init__(self, broker_url, aggregator):
        self.broker_url = broker_url
        self.aggregator = aggregator
        self.client = None

    def on_message(self, client, userdata, message):
        try:
            payload = json.loads(message.payload.decode())
            # Run async method in event loop
            asyncio.create_task(self.aggregator.process_pubsub_event(payload))
        except Exception as e:
            print(f"Error processing message: {e}")

    async def listen(self):
        # Parse broker URL (assuming format mqtt://host:port)
        if self.broker_url.startswith("mqtt://"):
            host_port = self.broker_url[7:].split(":")
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else 1883
        else:
            host = self.broker_url
            port = 1883

        self.client = mqtt.Client()
        self.client.on_message = self.on_message
        self.client.connect(host, port)
        self.client.subscribe("embrapac/data")  # Placeholder topic
        self.client.loop_start()

        # Keep running
        while True:
            await asyncio.sleep(1)