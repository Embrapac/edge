# data_aggregator/aggregator.py
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from shared.logger import get_struct_logger

logger = get_struct_logger(__name__)

@dataclass
class AggregatedEvent:
    timestamp: datetime
    pubsub_data: dict
    detections: list = field(default_factory=list)
    computed_metrics: dict = field(default_factory=dict)

class DataAggregator:
    def __init__(self, detection_queue: asyncio.Queue, output_queue: asyncio.Queue):
        self._detection_queue = detection_queue
        self._output_queue = output_queue
        self._latest_detections = []

    async def consume_detections(self):
        """Mantém a lista de detecções recentes atualizada."""
        while True:
            detection = await self._detection_queue.get()
            logger.info(f"Received detection on class {detection.get('class', 'unknown')} with confidence {detection.get('confidence', 0)} at {datetime.fromtimestamp(detection.get('timestamp', 'unknown'))}")
            self._latest_detections = detection  # substitui pela janela mais recente
            print(f"Updated latest detections: {self._latest_detections}")

    async def process_pubsub_event(self, event: dict):
        aggregated = AggregatedEvent(
            timestamp=datetime.now(datetime.timezone.utc),
            pubsub_data=event,
            detections=self._latest_detections.copy(),
        )
        aggregated.computed_metrics = self._calculate(aggregated)
        await self._output_queue.put(aggregated)

    def _calculate(self, event: AggregatedEvent) -> dict:
        # Ex: contagem de objetos, score médio, correlação com dados MQTT
        logger.debug(f"Calculating metrics for event with {len(event.detections)} detections and pubsub data: {event.pubsub_data}")

        for d in event.detections:
            logger.debug(f"Detection - class: {d.get('class', 'unknown')}, confidence: {d.get('confidence', 0)}, timestamp: {datetime.fromtimestamp(d.get('timestamp', 'unknown'))}")
        
        camera_detection_class = event.detections[0].get('class')
        camera_detection_conf = event.detections[0].get('confidence')
        camera_detection_time = event.detections[0].get('timestamp')
        mcu_detection_class = event.pubsub_data.get('class')
        mcu_detection_time = event.pubsub_data.get('timestamp')

        count = len(event.detections)
        avg_confidence = (
            sum(d.get("confidence", 0) for d in event.detections) / count
            if count else 0.0
        )
        return {"object_count": count, "avg_confidence": avg_confidence}
