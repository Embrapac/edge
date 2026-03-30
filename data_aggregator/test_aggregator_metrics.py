import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from datetime import datetime
from data_aggregator.aggregator import DataAggregator
from models.camera_detection import CameraDetection

TS_FMT = "%Y-%m-%d %H:%M:%S.%f"

# Fixed reference timestamps for deterministic assertions
TS_A = 1700000000.0  # 2023-11-14 22:13:20
TS_B = 1700000060.0  # TS_A + 60 s
TS_C = 1700000120.0  # TS_A + 120 s


def _det(object_class: str, confidence: float, timestamp: float) -> CameraDetection:
    return CameraDetection(object_class=object_class, confidence=confidence, timestamp=timestamp, bbox=[])


def _fmt(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime(TS_FMT)


class TestComputeCameraDetectionMetrics(unittest.TestCase):

    def setUp(self):
        import asyncio
        self.aggregator = DataAggregator(asyncio.Queue(), asyncio.Queue())

    def _call(self, detections):
        return self.aggregator._compute_camera_detection_metrics(detections)

    # ------------------------------------------------------------------
    # Edge cases: empty / single
    # ------------------------------------------------------------------

    def test_empty_list(self):
        result = self._call([])
        self.assertEqual(result["object_count"], 0)
        self.assertIsNone(result["dominant_class"])
        self.assertEqual(result["avg_confidence"], 0.0)
        self.assertIsNone(result["begin_timestamp"])
        self.assertIsNone(result["end_timestamp"])

    def test_single_detection(self):
        result = self._call([_det("cat", 0.9, TS_A)])
        self.assertEqual(result["object_count"], 1)
        self.assertEqual(result["dominant_class"], "cat")
        self.assertAlmostEqual(result["avg_confidence"], 0.9)
        self.assertEqual(result["begin_timestamp"], _fmt(TS_A))
        self.assertEqual(result["end_timestamp"], _fmt(TS_A))

    # ------------------------------------------------------------------
    # Dominant class
    # ------------------------------------------------------------------

    def test_dominant_class_clear_winner(self):
        detections = [
            _det("dog", 0.8, TS_A),
            _det("dog", 0.7, TS_B),
            _det("cat", 0.9, TS_C),
        ]
        result = self._call(detections)
        self.assertEqual(result["dominant_class"], "dog")

    def test_dominant_class_single_unique(self):
        detections = [_det("bird", 0.5, TS_A), _det("bird", 0.6, TS_B)]
        result = self._call(detections)
        self.assertEqual(result["dominant_class"], "bird")

    def test_dominant_class_all_different_classes(self):
        # With one of each, whichever has count==1 is valid; just assert it's one of the classes
        detections = [
            _det("cat", 0.9, TS_A),
            _det("dog", 0.8, TS_B),
            _det("bird", 0.7, TS_C),
        ]
        result = self._call(detections)
        self.assertIn(result["dominant_class"], {"cat", "dog", "bird"})

    def test_dominant_class_tie_resolved_by_max(self):
        # max() returns first max it encounters; just assert the result is one of the tied classes
        detections = [
            _det("cat", 0.9, TS_A),
            _det("dog", 0.8, TS_B),
        ]
        result = self._call(detections)
        self.assertIn(result["dominant_class"], {"cat", "dog"})

    # ------------------------------------------------------------------
    # Average confidence
    # ------------------------------------------------------------------

    def test_avg_confidence_uniform(self):
        detections = [_det("cat", 0.8, TS_A), _det("cat", 0.8, TS_B)]
        result = self._call(detections)
        self.assertAlmostEqual(result["avg_confidence"], 0.8)

    def test_avg_confidence_varied(self):
        detections = [
            _det("cat", 1.0, TS_A),
            _det("dog", 0.0, TS_B),
        ]
        result = self._call(detections)
        self.assertAlmostEqual(result["avg_confidence"], 0.5)

    def test_avg_confidence_zero(self):
        detections = [_det("cat", 0.0, TS_A), _det("cat", 0.0, TS_B)]
        result = self._call(detections)
        self.assertAlmostEqual(result["avg_confidence"], 0.0)

    def test_avg_confidence_max(self):
        detections = [_det("cat", 1.0, TS_A), _det("cat", 1.0, TS_B)]
        result = self._call(detections)
        self.assertAlmostEqual(result["avg_confidence"], 1.0)

    # ------------------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------------------

    def test_timestamps_ordered(self):
        detections = [_det("cat", 0.9, TS_B), _det("cat", 0.8, TS_A), _det("cat", 0.7, TS_C)]
        result = self._call(detections)
        self.assertEqual(result["begin_timestamp"], _fmt(TS_A))
        self.assertEqual(result["end_timestamp"], _fmt(TS_C))

    def test_timestamps_already_sorted(self):
        detections = [_det("cat", 0.9, TS_A), _det("cat", 0.8, TS_B), _det("cat", 0.7, TS_C)]
        result = self._call(detections)
        self.assertEqual(result["begin_timestamp"], _fmt(TS_A))
        self.assertEqual(result["end_timestamp"], _fmt(TS_C))

    def test_timestamps_reverse_sorted(self):
        detections = [_det("cat", 0.9, TS_C), _det("cat", 0.8, TS_B), _det("cat", 0.7, TS_A)]
        result = self._call(detections)
        self.assertEqual(result["begin_timestamp"], _fmt(TS_A))
        self.assertEqual(result["end_timestamp"], _fmt(TS_C))

    def test_timestamps_equal(self):
        detections = [_det("cat", 0.9, TS_A), _det("dog", 0.8, TS_A)]
        result = self._call(detections)
        self.assertEqual(result["begin_timestamp"], _fmt(TS_A))
        self.assertEqual(result["end_timestamp"], _fmt(TS_A))

    def test_timestamps_zero_excluded(self):
        # timestamp=0.0 is falsy; those entries should be excluded from begin/end
        detections = [_det("cat", 0.9, 0.0), _det("cat", 0.8, TS_B)]
        result = self._call(detections)
        self.assertEqual(result["begin_timestamp"], _fmt(TS_B))
        self.assertEqual(result["end_timestamp"], _fmt(TS_B))

    def test_timestamps_all_zero_returns_none(self):
        detections = [_det("cat", 0.9, 0.0), _det("cat", 0.8, 0.0)]
        result = self._call(detections)
        self.assertIsNone(result["begin_timestamp"])
        self.assertIsNone(result["end_timestamp"])

    # ------------------------------------------------------------------
    # Object count
    # ------------------------------------------------------------------

    def test_object_count(self):
        detections = [_det("cat", 0.9, TS_A), _det("dog", 0.8, TS_B), _det("bird", 0.7, TS_C)]
        result = self._call(detections)
        self.assertEqual(result["object_count"], 3)

    # ------------------------------------------------------------------
    # Return structure
    # ------------------------------------------------------------------

    def test_return_keys(self):
        result = self._call([_det("cat", 0.9, TS_A)])
        expected_keys = {"object_count", "dominant_class", "avg_confidence", "begin_timestamp", "end_timestamp"}
        self.assertEqual(set(result.keys()), expected_keys)


if __name__ == "__main__":
    unittest.main()
