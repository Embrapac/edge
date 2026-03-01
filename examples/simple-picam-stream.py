#!/usr/bin/python3
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
import time

RESOLUTION = (640, 480)
FRAME_RATE = 30
RTSP_URL = "rtsp://localhost:8554/camera"

picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": RESOLUTION}))
picam2.start()

output = FfmpegOutput(RTSP_URL, audio=False)
encoder = H264Encoder()

print("Streamando para RTSP...")
picam2.start_encoder(encoder, output)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    picam2.stop_encoder()
    picam2.stop()
    print("Parado!")
