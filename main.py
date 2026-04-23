import asyncio
import argparse
import json
from shared.event_bus import EventBus
from shared.healthcheck import HealthCheck
from shared.logger import get_logger, get_struct_logger
from video_buffer.buffer_manager import VideoBufferManager
from video_buffer.capture_writer import CaptureWriter
from data_aggregator.aggregator import DataAggregator
from data_aggregator.subscriber import PubSubSubscriber, PubSubPublisher
from data_aggregator.uart_subscriber import UARTPublisher, UARTSubscriber
from inference.model_manager import ModelManager
from inference.model_manager import ModelFetcher
from config import Config

logger = get_struct_logger(__name__)

async def main(
    show_debug_window,
    general_server_ip,
    stream_server_ip,
    mqtt_broker_port,
    timestamp_tolerance_sec,
):
    logger.info("Starting main orchestrator")
    event_bus = EventBus()
    health_check = HealthCheck()
    streamer_url = Config.build_streamer_url(stream_server_ip)
    broker_url = Config.build_broker_url(general_server_ip, mqtt_broker_port)
    
    # Module 1: Video Buffer
    buffer_mgr = VideoBufferManager(Config.VIDEO_STORAGE_PATH)
    capture_writer = CaptureWriter(
        buffer_mgr,
        event_bus.detection_queue,
        streamer_url=streamer_url,
        model_path=Config.DEFAULT_MODEL_PATH,
        source=Config.VIDEO_SOURCE,
        resolution=Config.VIDEO_RESOLUTION,
        threshold=Config.DETECTION_THRESHOLD,
        show_window=show_debug_window,
        record=Config.RECORD_VIDEO,
        record_path=Config.RECORD_PATH,
        record_fps=Config.RECORD_FPS,
    )
    # Module 2: Aggregator
    aggregator = DataAggregator(
        event_bus.detection_queue,
        event_bus.output_queue,
        input_queue=event_bus.input_queue,
        timestamp_tolerance_sec=timestamp_tolerance_sec,
    )
    subscriber = PubSubSubscriber(broker_url, aggregator)
    publisher = PubSubPublisher(general_server_ip, mqtt_broker_port)
    uart_publisher = UARTPublisher(
        Config.UART_PORT,
        Config.UART_BAUDRATE,
        timeout=Config.UART_TIMEOUT,
    )
    uart_subscriber = UARTSubscriber(
        Config.UART_PORT,
        Config.UART_BAUDRATE,
        aggregator,
        timeout=Config.UART_TIMEOUT,
    )
    # Module 3: Inference
    model_mgr = ModelManager(Config.MODELS_DIR)
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
                publisher.publish(Config.MQTT_TOPIC_METRICS, json.dumps(aggregated.computed_metrics))
                # Only publish detection counts if MCU class was identified
                if aggregated.computed_metrics.get("mcu_class"):
                    publisher.publish(Config.MQTT_TOPIC_DATA_DETECTIONS, json.dumps({
                        "detected_class": aggregated.computed_metrics.get("mcu_class"),
                        "mcu_timestamp": aggregated.computed_metrics.get("mcu_timestamp"),
                    }))
                if aggregated.uart_data.get("status"):
                    publisher.publish(Config.MQTT_TOPIC_CBELT_ACTUATOR, json.dumps({
                        "status": aggregated.uart_data.get("status"),
                        "state": aggregated.uart_data.get("state"),
                    }))
                if aggregated.uart_data.get("state") == "EMERGENCY":
                    publisher.publish(Config.MQTT_TOPIC_CBELT_ACTUATOR, json.dumps({
                        "state": aggregated.uart_data.get("state"),
                    }))
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

    async def safe_consume_input():
        try:
            await aggregator.consume_input_events(uart_publisher)
        except Exception as e:
            logger.error(f"Input queue processing error: {e}")

    async def safe_listen():
        try:
            await subscriber.listen()
        except Exception as e:
            logger.error(f"Subscriber error: {e}")

    async def safe_listen_uart():
        if not Config.UART_ENABLED:
            logger.info("UART subscriber is disabled by configuration")
            return
        try:
            await uart_subscriber.listen()
        except Exception as e:
            logger.error(f"UART subscriber error: {e}")

    await asyncio.gather(
        safe_capture(),
        safe_aggregate(),
        safe_consume_input(),
        safe_listen(),
        safe_listen_uart(),
        # TODO: waiting on remote location definition for model updates
        # check_model_updates(),
        process_output(),
        run_health_checks(),
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Edge detection orchestrator")
    parser.add_argument(
        "--general-server-ip",
        default=Config.DEFAULT_GENERAL_SERVER_IP,
        help="backend server IP",
    )
    parser.add_argument(
        "--stream-server-ip",
        default=Config.DEFAULT_STREAM_SERVER_IP,
        help="stream server IP",
    )
    parser.add_argument(
        "--mqtt-broker-port",
        type=int,
        default=Config.DEFAULT_MQTT_BROKER_PORT,
        help="MQTT broker port",
    )
    parser.add_argument(
        "--timestamp-tolerance-sec",
        type=float,
        default=Config.DEFAULT_TIMESTAMP_TOLERANCE_SEC,
        help="Timestamp tolerance in seconds for aggregator correlation",
    )
    parser.add_argument(
        "--show-detection-window",
        type=lambda x: x.lower() in ('true', '1', 'yes', 'on'),
        nargs='?',
        const=True,
        default=Config.SHOW_DETECTION_WINDOW,
        help="Enable the debug window display (accepts: true/false)",
    )
    
    args = parser.parse_args()
    
    asyncio.run(
        main(
            show_debug_window=args.show_detection_window,
            general_server_ip=args.general_server_ip,
            stream_server_ip=args.stream_server_ip,
            mqtt_broker_port=args.mqtt_broker_port,
            timestamp_tolerance_sec=args.timestamp_tolerance_sec,
        )
    )
