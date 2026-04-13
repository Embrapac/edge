import asyncio
import httpx
from shared.logger import get_logger, get_struct_logger

logger = get_struct_logger(__name__)

class VideoStreamer:
    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip("/")
        self.session = None
        self._consecutive_failures = 0

    async def __aenter__(self):
        self.session = httpx.AsyncClient()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.aclose()

    async def stream_frame(self, frame_bytes: bytes):
        """Stream a frame to the on-premises server.

        Uses an exponential backoff strategy when streaming fails repeatedly.
        After 3 consecutive failures, delays will be applied before each retry.
        """
        try:
            # Accept either a base URL (e.g. http://host/stream) or a full
            # endpoint URL (e.g. http://host/stream/upload).
            upload_url = self.server_url
            if not upload_url.endswith("/upload"):
                upload_url = f"{upload_url}/upload"

            response = await self.session.post(
                upload_url,
                content=frame_bytes,
                headers={"Content-Type": "application/octet-stream"}
            )
            response.raise_for_status()
            self._consecutive_failures = 0
            logger.debug("Frame streamed successfully")
        except Exception as e:
            self._consecutive_failures += 1
            if self._consecutive_failures > 3:
                # Exponential backoff: 2^(n-3) seconds, capped at 30s
                backoff_seconds = min(2 ** (self._consecutive_failures - 3), 30)
                logger.warning(
                    "Stream frame failed %d times, backing off for %ds: %s",
                    self._consecutive_failures,
                    backoff_seconds,
                    e,
                )
                await asyncio.sleep(backoff_seconds)
            else:
                logger.error(
                    "Failed to stream frame (attempt %d): %s",
                    self._consecutive_failures,
                    e,
                )

# Usage in CaptureWriter: integrate streaming
# In CaptureWriter.run(), after capturing frame:
# async with VideoStreamer("http://on-premises-server:port") as streamer:
#     await streamer.stream_frame(frame.tobytes())