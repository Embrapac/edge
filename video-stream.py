from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder, H264Encoder
from picamera2.outputs import FileOutput, FfmpegOutput, CircularOutput
import io
from threading import Condition
from flask import Flask, Response

RESOLUTION = (640, 480)
FRAME_RATE = 30

app = Flask(__name__)

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()
    
    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(
        main={"size": RESOLUTION}),
        controls={"FrameRate": FRAME_RATE}
    )

encoder = JpegEncoder()
stream_output = StreamingOutput()
file_output = FfmpegOutput('recording.mp4', audio=False)

encoder.output = [FileOutput(stream_output), file_output]

picam2.start_encoder(encoder)
picam2.start()

def generate_frames():
    while True:
        with stream_output.condition:
            stream_output.condition.wait()
            frame = stream_output.frame
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
