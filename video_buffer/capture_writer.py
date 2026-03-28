
import asyncio
import cv2
import threading
import queue
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
        self.frame_count = 0  # For frame skipping in display
        self.display_skip = 2  # Show every 2nd frame in debug window

        # Display thread setup
        self.display_queue = queue.Queue(maxsize=5)  # Buffer up to 5 frames
        self.display_thread = None
        self.display_running = False
        self._stream_task = None

    async def run(self):
        logger.info(f"CaptureWriter starting with model={self.model_path}, source={self.source}")

        # Load YOLO model
        if not Path(self.model_path).exists():
            logger.error(f"Model not found at path: {self.model_path}")
            return

        self.model = YOLO(self.model_path, task="detect")
        labels = self.model.names

        # Parse resolution early for source initialization (needed for Picamera)
        res_w, res_h = None, None
        if self.resolution:
            try:
                res_w, res_h = map(int, str(self.resolution).split("x"))
            except Exception:
                logger.warning(f"Invalid resolution format {self.resolution}, using native camera resolution")
                res_w = res_h = None

        # Open video source
        source_arg = self.source
        self.picamera = None
        self.cap = None
        try:
            if isinstance(source_arg, str) and source_arg.startswith("picamera"):
                # picamera0, picamera1, or picamera
                from picamera2 import Picamera2

                picam_idx = 0
                if len(source_arg) > 8 and source_arg[8:].isdigit():
                    picam_idx = int(source_arg[8:])

                self.picamera = Picamera2()

                # Configure picamera with requested resolution (if provided)
                cam_size = (res_w, res_h) if res_w and res_h else (640, 480)
                self.picamera.configure(
                    self.picamera.create_video_configuration(
                        main={"format": "RGB888", "size": cam_size}
                    )
                )
                self.picamera.start()

            else:
                if isinstance(source_arg, str) and source_arg.isdigit():
                    source_arg = int(source_arg)
                self.cap = cv2.VideoCapture(source_arg)
                if not self.cap.isOpened():
                    raise RuntimeError(f"Error: Could not open video source {source_arg}")

                if res_w and res_h:
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, res_w)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, res_h)

        except Exception as e:
            logger.error(f"Failed to open video source {source_arg}: {e}")
            return

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

        # Start display thread if needed
        if self.show_window:
            self.display_running = True
            self.display_thread = threading.Thread(target=self._display_thread, daemon=True)
            self.display_thread.start()
            logger.info("Display thread initialized")

        async with VideoStreamer(self.streamer_url) as streamer:
            while True:
                # Offload blocking capture + inference to thread pool so the asyncio
                # event loop is free between frames — this is what keeps capture responsive.
                ret, frame = await asyncio.to_thread(self._capture_frame)
                if not ret or frame is None:
                    logger.warning("Could not read frame from source, closing capture loop")
                    break

                if res_w and res_h:
                    frame = await asyncio.to_thread(cv2.resize, frame, (res_w, res_h))

                # Run inference in thread pool (CPU-bound; blocks event loop if called directly)
                results = await asyncio.to_thread(lambda: self.model(frame, verbose=False))
                detections = self._process_results(results, labels)

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
                    # Keep streaming decoupled from inference to avoid backoff delays blocking detection.
                    if self._stream_task is None or self._stream_task.done():
                        self._stream_task = asyncio.create_task(streamer.stream_frame(jpeg.tobytes()))

                # Display UI if requested
                if self.show_window and self.display_running:
                    self.frame_count += 1
                    # Show every Nth frame to reduce display overhead
                    if self.frame_count % self.display_skip == 0:
                        try:
                            # Non-blocking put - drop frame if queue full
                            self.display_queue.put_nowait(annotated_frame.copy())
                        except queue.Full:
                            # Drop oldest frame if queue full
                            try:
                                self.display_queue.get_nowait()
                                self.display_queue.put_nowait(annotated_frame.copy())
                            except queue.Empty:
                                pass

                await asyncio.to_thread(self.buffer_manager.enforce_limit)

                # Rate control
                await asyncio.sleep(0.02)

            if self._stream_task is not None and not self._stream_task.done():
                self._stream_task.cancel()
                try:
                    await self._stream_task
                except asyncio.CancelledError:
                    pass

        self._cleanup()

    def _display_thread(self):
        """Separate thread for OpenCV display to avoid blocking main loop"""
        logger.info("Display thread started")
        while self.display_running:
            try:
                # Non-blocking get with timeout
                frame = self.display_queue.get(timeout=0.1)
                cv2.imshow('YOLO Edge Feed', frame)
                key = cv2.waitKey(5) & 0xFF
                if key == ord('q'):
                    logger.info('Quit pressed in display thread')
                    self.display_running = False
                    break
                elif key == ord('s'):
                    logger.info('Pause pressed in display thread')
                    cv2.waitKey(0)
                elif key == ord('p'):
                    capture_path = 'capture.png'
                    cv2.imwrite(capture_path, frame)
                    logger.info(f'Saved capture to {capture_path}')
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Display thread error: {e}")
                break
        cv2.destroyAllWindows()
        logger.info("Display thread stopped")

    def _process_results(self, results, labels):
        detections = []
        # results may be list of ultralytics Results objects
        for result in results:
            if not hasattr(result, 'boxes'):
                continue
            for box in result.boxes:
                confidence = float(box.conf)
                if confidence < self.threshold:
                    continue
                classidx = int(box.cls.item())
                classname = labels[classidx]
                detection = {
                    'class': classname,
                    'confidence': confidence,
                    'bbox': [float(x) for x in box.xyxy.tolist()[0]] if hasattr(box.xyxy, 'tolist') else list(box.xyxy),
                    'timestamp': time.time(),
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

    def _capture_frame(self):
        if self.picamera is not None:
            frame = self.picamera.capture_array()
            return (frame is not None, frame)

        if self.cap is not None:
            ret, frame = self.cap.read()
            return (ret, frame)

        return (False, None)

    def _cleanup(self):
        logger.info("Starting cleanup...")

        # Stop display thread
        if self.display_running:
            self.display_running = False
            if self.display_thread and self.display_thread.is_alive():
                self.display_thread.join(timeout=1.0)
                logger.info("Display thread joined")

        if self.cap is not None:
            self.cap.release()
        if self.picamera is not None:
            try:
                self.picamera.stop()
            except Exception as err:
                logger.warning(f"Failed to stop Picamera: {err}")
        if self.writer is not None:
            self.writer.release()
        cv2.destroyAllWindows()
        logger.info("Cleanup completed")
