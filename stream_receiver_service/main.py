# pyright: reportMissingImports=false

import asyncio
import logging
import time
from typing import AsyncIterator, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, StreamingResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger("stream_receiver")

app = FastAPI(title="EDGE Stream Receiver", version="1.0.0")


class FrameStore:
    """Stores the most recent frame and ingestion counters in memory."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.latest_frame: Optional[bytes] = None
        self.latest_timestamp: Optional[float] = None
        self.total_frames: int = 0

    async def update(self, frame_bytes: bytes) -> dict:
        now = time.time()
        async with self._lock:
            self.latest_frame = frame_bytes
            self.latest_timestamp = now
            self.total_frames += 1
            return {
                "frame_id": self.total_frames,
                "timestamp": now,
                "size_bytes": len(frame_bytes),
            }

    async def snapshot(self) -> dict:
        async with self._lock:
            return {
                "has_frame": self.latest_frame is not None,
                "last_frame_at": self.latest_timestamp,
                "total_frames": self.total_frames,
            }


frame_store = FrameStore()


@app.get("/stream/health")
async def health() -> dict:
    stats = await frame_store.snapshot()
    return {"status": "ok", **stats}


@app.post("/stream/upload")
async def upload_frame(request: Request) -> dict:
    frame_bytes = await request.body()
    if not frame_bytes:
        raise HTTPException(status_code=400, detail="Empty body")

    info = await frame_store.update(frame_bytes)
    logger.info(
        "Frame received id=%s size=%s",
        info["frame_id"],
        info["size_bytes"],
    )
    return {"status": "received", **info}


@app.get("/stream/latest.jpg")
async def latest_frame() -> Response:
    if frame_store.latest_frame is None:
        raise HTTPException(status_code=404, detail="No frame received yet")
    return Response(content=frame_store.latest_frame, media_type="image/jpeg")


@app.get("/stream/mjpeg")
async def mjpeg_stream() -> StreamingResponse:
    boundary = "frame"

    async def generator() -> AsyncIterator[bytes]:
        while True:
            if frame_store.latest_frame is None:
                await asyncio.sleep(0.1)
                continue

            yield (
                b"--" + boundary.encode("utf-8") + b"\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + frame_store.latest_frame
                + b"\r\n"
            )
            await asyncio.sleep(0.1)

    return StreamingResponse(
        generator(),
        media_type=f"multipart/x-mixed-replace; boundary={boundary}",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
