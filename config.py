class Config:
    VIDEO_STORAGE_PATH = "/tmp"
    STREAMER_URL = "http://10.7.202.108:8000/stream"
    BROKER_URL = "mqtt://localhost:1883"
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
    MQTT_TOPIC_DETECTIONS = "embrapac/edge/mcu-data"
    MQTT_TOPIC_METRICS = "embrapac/edge/aggregated-metrics"
    MQTT_PUBLISHER_HOST = "10.7.202.10"
    MQTT_PUBLISHER_PORT = 11883
