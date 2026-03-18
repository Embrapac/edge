
import asyncio

class EventBus:
    def __init__(self):
        self._subscribers = []
        self.detection_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()

    def subscribe(self, callback):
        self._subscribers.append(callback)

    def publish(self, event):
        for callback in self._subscribers:
            callback(event)