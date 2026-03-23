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
            self._latest_detections = detection  # substitui pela janela mais recente

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
        count = len(event.detections)
        avg_confidence = (
            sum(d.get("confidence", 0) for d in event.detections) / count
            if count else 0.0
        )
        return {"object_count": count, "avg_confidence": avg_confidence}
