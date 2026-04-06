import asyncio
import argparse
from shared.event_bus import EventBus
from shared.healthcheck import HealthCheck
from shared.logger import get_logger, get_struct_logger
from video_buffer.buffer_manager import VideoBufferManager
from video_buffer.capture_writer import CaptureWriter
from data_aggregator.aggregator import DataAggregator
from data_aggregator.subscriber import PubSubSubscriber
from inference.model_manager import ModelManager
from inference.model_manager import ModelFetcher
from config import Config

logger = get_struct_logger(__name__)

async def main(show_debug_window):
    logger.info("Starting main orchestrator")
    event_bus = EventBus()
    health_check = HealthCheck()
    
    # Módulo 1: Buffer de vídeo
    buffer_mgr = VideoBufferManager(Config.VIDEO_STORAGE_PATH)
    capture_writer = CaptureWriter(
        buffer_mgr,
        event_bus.detection_queue,
        streamer_url=Config.STREAMER_URL,
        model_path=Config.DEFAULT_MODEL_PATH,
        source=Config.VIDEO_SOURCE,
        resolution=Config.VIDEO_RESOLUTION,
        threshold=Config.DETECTION_THRESHOLD,
        show_window=show_debug_window,
        record=Config.RECORD_VIDEO,
        record_path=Config.RECORD_PATH,
        record_fps=Config.RECORD_FPS,
    )

    # Módulo 2: Agregador
    aggregator = DataAggregator(event_bus.detection_queue, event_bus.output_queue)
    subscriber = PubSubSubscriber(Config.BROKER_URL, aggregator)

    # Módulo 3: Inferência
    model_mgr = ModelManager(Config.MODELS_DIR)
    # model_fetcher = ModelFetcher(model_mgr, Config.MODELS_DIR)

    model_mgr.load_model(Config.DEFAULT_MODEL_PATH)

    # Task for health checks
    async def run_health_checks():
        while True:
            status = health_check.check()
            logger.info(f"Health check: {status}")
            await asyncio.sleep(60)  # Check every 60 seconds

    # Task for model updates
    # TODO: Check for remote location configuration first
    # async def check_model_updates():
    #     while True:
    #         try:
    #             # Placeholder: Check for model updates from a remote endpoint
    #             # For now, simulate by trying to fetch a model
    #             model_url = "http://example.com/new_model.onnx"  # Replace with actual URL
    #             await model_fetcher.fetch_and_apply(model_url, "new_model.onnx")
    #         except Exception as e:
    #             logger.error(f"Model update failed: {e}")
    #         await asyncio.sleep(60)  # Check every 60 seconds

    # Task for processing output queue
    async def process_output():
        while True:
            try:
                aggregated = await event_bus.output_queue.get()
                # Store locally (placeholder)
                logger.info(f"Storing aggregated data: {aggregated}")
                # TODO: Implement local storage logic
            except Exception as e:
                logger.error(f"Error processing output: {e}")

    # Wrap tasks with error handling
    async def safe_capture():
        try:
            await capture_writer.run()
        except Exception as e:
            logger.error(f"Capture writer error: {e}")

    async def safe_aggregate():
        try:
            await aggregator.consume_detections()
        except Exception as e:
            logger.error(f"Aggregator error: {e}")

    async def safe_listen():
        try:
            await subscriber.listen()
        except Exception as e:
            logger.error(f"Subscriber error: {e}")

    await asyncio.gather(
        safe_capture(),
        safe_aggregate(),
        safe_listen(),
        # TODO: waiting on remote location definition for model updates
        # check_model_updates(),
        process_output(),
        run_health_checks(),
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Edge detection orchestrator")
    parser.add_argument(
        "--show-detection-window",
        type=lambda x: x.lower() in ('true', '1', 'yes', 'on'),
        nargs='?',
        const=True,
        default=Config.SHOW_DETECTION_WINDOW,
        help="Enable the detection window display (accepts: true/false)",
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(show_debug_window=args.show_detection_window))
