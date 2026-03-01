#!/usr/bin/python3
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
import time

RTSP_URL = "rtsp://localhost:8554/camera"  # sem auth
RESOLUTION = (640, 480)

picam2 = Picamera2()
picam2.configure(
    picam2.create_video_configuration(
        main={"size": RESOLUTION},
    )
)

encoder = H264Encoder(bitrate=2_000_000)

output = FfmpegOutput(
    f"-f rtsp -rtsp_transport tcp {RTSP_URL}",
    audio=False
)

print("Iniciando câmera...")
picam2.start()
print(f"Publicando em {RTSP_URL} ... (Ctrl+C para parar)")

try:
    picam2.start_encoder(encoder, output)
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Parando...")
    picam2.stop_encoder()
    picam2.stop()
