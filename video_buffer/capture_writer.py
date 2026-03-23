
import asyncio
import cv2
from ultralytics import YOLO
import time
from pathlib import Path
from ultralytics import YOLO

from .uploader import VideoStreamer
from shared.logger import get_struct_logger
from config import Config

logger = get_struct_logger(__name__)


class CaptureWriter:
    def __init__(
        self,
        buffer_manager,
        detection_queue,
        streamer_url=Config.STREAMER_URL,
        model_path=Config.DEFAULT_MODEL_PATH,
        source=Config.VIDEO_SOURCE,
        resolution=Config.VIDEO_RESOLUTION,
        threshold=Config.DETECTION_THRESHOLD,
        show_window=Config.SHOW_DETECTION_WINDOW,
        record=Config.RECORD_VIDEO,
        record_path=Config.RECORD_PATH,
        record_fps=Config.RECORD_FPS,
        stream_quality=Config.FRAME_STREAM_QUALITY,
    ):
        self.buffer_manager = buffer_manager
        self.detection_queue = detection_queue
        self.streamer_url = streamer_url
        # Placeholder for model - will be replaced with user's RPi5 code
        self.model_path = model_path
        self.source = source
        self.threshold = threshold
        self.show_window = show_window
        self.record = record
        self.record_path = record_path
        self.record_fps = record_fps
        self.stream_quality = stream_quality

        self.model = None
        self.cap = None
        self.writer = None
        self.resolution = resolution

    async def run(self):
        logger.info(f"CaptureWriter starting with model={self.model_path}, source={self.source}")

        # Load YOLO model
        if not Path(self.model_path).exists():
            logger.error(f"Model not found at path: {self.model_path}")
            return

        self.model = YOLO(self.model_path, task="detect")

        # Open video source
        source_arg = self.source
        try:
            if isinstance(source_arg, str) and source_arg.isdigit():
                source_arg = int(source_arg)
            self.cap = cv2.VideoCapture(source_arg)
        except Exception as e:
            logger.error(f"Failed to open video source {source_arg}: {e}")
            return

        if not self.cap.isOpened():
            logger.error(f"Error: Could not open video source {source_arg}")
            return

        # Parse resolution
        res_w, res_h = None, None
        if self.resolution:
            try:
                res_w, res_h = map(int, str(self.resolution).split("x"))
            except Exception:
                logger.warning(f"Invalid resolution format {self.resolution}, using native camera resolution")
                res_w = res_h = None

        if self.record and (res_w is None or res_h is None):
            # try to infer from source if resolution not provided
            native_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            native_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if native_w and native_h:
                res_w, res_h = native_w, native_h

        if self.record and res_w and res_h:
            self.writer = cv2.VideoWriter(
                self.record_path,
                cv2.VideoWriter_fourcc(*"MJPG"),
                self.record_fps,
                (res_w, res_h),
            )
            logger.info(f"Recording configured to {self.record_path} ({res_w}x{res_h}@{self.record_fps})")

        async with VideoStreamer(self.streamer_url) as streamer:
            while True:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    logger.warning("Could not read frame from source, closing capture loop")
                    break

                if res_w and res_h:
                    frame = cv2.resize(frame, (res_w, res_h))

                # Run inference
                results = self.model(frame, verbose=False)
                detections = self._process_results(results)

                # Publish detections to queue
                await self.detection_queue.put(detections)

                # Draw boxes optionally
                annotated_frame = self._draw_boxes(frame.copy(), detections)

                # Record video if requested
                if self.writer is not None:
                    self.writer.write(annotated_frame)

                # Stream frame as JPEG bytes
                success, jpeg = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, self.stream_quality])
                if success:
                    await streamer.stream_frame(jpeg.tobytes())

                # Display UI if requested
                if self.show_window:
                    cv2.imshow('YOLO Edge Feed', annotated_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        logger.info('Quit pressed; exiting capture loop')
                        break
                    elif key == ord('s'):
                        logger.info('Pause pressed; waiting for key')
                        cv2.waitKey(0)
                    elif key == ord('p'):
                        capture_path = 'capture.png'
                        cv2.imwrite(capture_path, annotated_frame)
                        logger.info(f'Saved capture to {capture_path}')

                self.buffer_manager.enforce_limit()

                # Rate control
                await asyncio.sleep(0.01)

        self._cleanup()

    def _process_results(self, results):
        detections = []
        # results may be list of ultralytics Results objects
        for result in results:
            if not hasattr(result, 'boxes'):
                continue
            for box in result.boxes:
                confidence = float(box.conf)
                if confidence < self.threshold:
                    continue
                detection = {
                    'class': int(box.cls.item()) if hasattr(box.cls, 'item') else int(box.cls),
                    'confidence': confidence,
                    'bbox': [float(x) for x in box.xyxy.tolist()[0]] if hasattr(box.xyxy, 'tolist') else list(box.xyxy),
                }
                detections.append(detection)
        return detections

    def _draw_boxes(self, frame, detections):
        for d in detections:
            x1, y1, x2, y2 = map(int, d['bbox'])
            cls_id = d.get('class', 0)
            confidence = d.get('confidence', 0.0)
            label = f"{cls_id}:{confidence:.2f}"
            color = (0, 255, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        return frame

    def _cleanup(self):
        if self.cap is not None:
            self.cap.release()
        if self.writer is not None:
            self.writer.release()
        cv2.destroyAllWindows()
