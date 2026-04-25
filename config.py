class Config:
    VIDEO_STORAGE_PATH = "/tmp"
    DEFAULT_GENERAL_SERVER_IP = "10.7.202.10"
    DEFAULT_STREAM_SERVER_IP = "10.7.202.108"
    DEFAULT_MQTT_BROKER_PORT = 11883
    DEFAULT_TIMESTAMP_TOLERANCE_SEC = 3.0
    STREAM_SERVER_PORT = 8000
    STREAM_SERVER_PATH = "/stream"
    STREAMER_URL = f"http://{DEFAULT_STREAM_SERVER_IP}:{STREAM_SERVER_PORT}{STREAM_SERVER_PATH}"
    BROKER_URL = f"mqtt://{DEFAULT_GENERAL_SERVER_IP}:{DEFAULT_MQTT_BROKER_PORT}"
    UART_ENABLED = True
    UART_PORT = "/dev/ttyAMA0"
    UART_BAUDRATE = 9600
    UART_TIMEOUT = 1.0
    MODELS_DIR = "models"
    DEFAULT_MODEL_PATH = "models/product-sizingv3.pt"

    # Inference settings
    VIDEO_SOURCE = 'picamera1'          # camera index, or path to video file
    VIDEO_RESOLUTION = "640x480"        # specify WxH or None to keep native
    DETECTION_THRESHOLD = 0.5
    SHOW_DETECTION_WINDOW = False        # enable/disable debug window with detections
    RECORD_VIDEO = False
    RECORD_PATH = "recorded_output.avi"
    RECORD_FPS = 20
    FRAME_STREAM_QUALITY = 70           # JPEG quality for frame streaming

    # MQTT topics
    MQTT_TOPIC_METRICS = "embrapac/edge/aggregated-metrics"
    MQTT_TOPIC_DATA_DETECTIONS = "embrapac/edge/count"
    MQTT_TOPIC_CBELT_STATUS = "embrapac/edge/cbelt"
    MQTT_TOPIC_CBELT_ACTUATOR = "embrapac/edge/cbelt/status"
    MQTT_PUBLISHER_HOST = DEFAULT_GENERAL_SERVER_IP
    MQTT_PUBLISHER_PORT = DEFAULT_MQTT_BROKER_PORT

    UART_COMMAND_ENCODINGS = {
        ("control_cbelt", "START"): "10000000",
        ("control_cbelt", "STOP"):  "00100000",
        ("control_cbelt", "EMERGENCY"): "01000000",
        ("control_cbelt", "RESET"):     "01010000",
    }

    @classmethod
    def build_streamer_url(cls, host: str) -> str:
        return f"http://{host}:{cls.STREAM_SERVER_PORT}{cls.STREAM_SERVER_PATH}"

    @staticmethod
    def build_broker_url(host: str, port: int) -> str:
        return f"mqtt://{host}:{port}"
