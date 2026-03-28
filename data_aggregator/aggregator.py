# data_aggregator/aggregator.py
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from shared.logger import get_struct_logger
from models.camera_detection import CameraDetection, from_json

logger = get_struct_logger(__name__)

TS_FMT = "%Y-%m-%d %H:%M:%S.%f"

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
            logger.info(f"Received detection_queue {detection}")
            camera_detection = from_json(detection[0])  # Assuming detection is a JSON string; adjust if it's already a dict
            # TODO: adicionar detecção à lista. No calculo do agregado é que pode ser feita a comparação de todas detecções e decidir qual será.
            self._latest_detections.append(camera_detection)  # substitui pela janela mais recente
            logger.debug(f"Updated latest detections: {self._latest_detections}")

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
        logger.info(f"Calculating metrics for event with {len(event.detections)} detections and pubsub data: {event.pubsub_data}")

        for d in event.detections:
            logger.debug(f"Detection - class: {d.object_class}, confidence: {d.confidence}, timestamp: {datetime.fromtimestamp(d.timestamp).strftime(TS_FMT)}")
        camera_detection_metrics = self._compute_camera_detection_metrics(event.detections)

        for key, value in event.pubsub_data.items():
            logger.debug(f"PubSub data - {key}: {value}")
        mcu_detection_class = event.pubsub_data.get('class', 'unknown')
        mcu_detection_timestamp = event.pubsub_data.get('timestamp')

        # Cross-check: class agreement
        class_match = mcu_detection_class == camera_detection_metrics.get('dominant_class')
        if class_match:
            logger.info(f"Class match: MCU class '{mcu_detection_class}' matches dominant camera class '{camera_detection_metrics.get('dominant_class')}'")
        else:
            logger.warning(f"Class mismatch: MCU class '{mcu_detection_class}' does NOT match dominant camera class '{camera_detection_metrics.get('dominant_class')}'")
            logger.warning("Discarding this samples due class mismatch")
            return None
        # Cross-check: MCU timestamp within camera detection window
        raw_timestamps = [d.timestamp for d in event.detections if d.timestamp]
        if mcu_detection_timestamp is not None and raw_timestamps:
            mcu_ts = float(mcu_detection_timestamp)
            ts_in_range = min(raw_timestamps) <= mcu_ts <= max(raw_timestamps)
        else:
            ts_in_range = None

        mcu_detection_time = datetime.fromtimestamp(float(mcu_detection_timestamp)).strftime(TS_FMT) if mcu_detection_timestamp else None
        logger.info(f"Cross-check: object_class={mcu_detection_class}, mcu_detection_time={mcu_detection_time}")

        return {
            "mcu_class": mcu_detection_class,
            "mcu_timestamp": mcu_detection_time,
            "class_match": class_match,
            "mcu_ts_in_range": ts_in_range,
        }



    def _compute_camera_detection_metrics(self, detections: list) -> dict:
        count = len(detections)

        # Most identified class
        class_counts: dict[str, int] = {}
        for d in detections:
            class_counts[d.object_class] = class_counts.get(d.object_class, 0) + 1
        dominant_class = max(class_counts, key=class_counts.get) if class_counts else None

        # Average confidence
        avg_confidence = (
            sum(d.confidence for d in detections) / count
            if count else 0.0
        )

        # Begin and end timestamps
        timestamps = [d.timestamp for d in detections if d.timestamp]
        begin_ts = datetime.fromtimestamp(min(timestamps)).strftime(TS_FMT) if timestamps else None
        end_ts   = datetime.fromtimestamp(max(timestamps)).strftime(TS_FMT) if timestamps else None

        return {
            "object_count": count,
            "dominant_class": dominant_class,
            "avg_confidence": avg_confidence,
            "begin_timestamp": begin_ts,
            "end_timestamp": end_ts,
        }
