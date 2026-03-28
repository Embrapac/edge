
# the detection object has this format: {"class": "object_class", "confidence": 0.85, "timestamp": 1690000000.0, bbox: [x1, y1, x2, y2]}
import json
import string


def from_json(json_data: string) -> 'CameraDetection':
    data = json.loads(json_data)
    return CameraDetection(
        object_class=data.get("class", "unknown"),
        confidence=data.get("confidence", 0.0),
        timestamp=data.get("timestamp", 0.0),
        bbox=data.get("bbox", [])
    )

class CameraDetection:
    def __init__(self, object_class: str, confidence: float, timestamp: float, bbox: list):
        self.object_class = object_class
        self.confidence = confidence
        self.timestamp = timestamp
        self.bbox = bbox

    def to_dict(self):
        return {
            "class": self.object_class,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "bbox": self.bbox
        }