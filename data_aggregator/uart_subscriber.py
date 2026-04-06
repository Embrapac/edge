import asyncio
import json
from typing import Any

import serial

from shared.logger import get_struct_logger

logger = get_struct_logger(__name__)


class UARTSubscriber:
    def __init__(self, port: str, baudrate: int, aggregator, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.aggregator = aggregator
        self.timeout = timeout
        self.serial_conn = None

    def _parse_line(self, raw_line: str) -> dict[str, Any] | None:
        if not raw_line:
            return None

        # First try JSON payloads, which are the preferred format.
        try:
            payload = json.loads(raw_line)
            if isinstance(payload, dict):
                return payload
            logger.warning(f"UART payload is not a JSON object: {raw_line}")
            return None
        except json.JSONDecodeError:
            pass

        # Fallback: key=value pairs separated by comma/semicolon.
        pairs = [p.strip() for p in raw_line.replace(";", ",").split(",") if p.strip()]
        payload: dict[str, Any] = {}
        for pair in pairs:
            if "=" not in pair:
                continue
            key, value = pair.split("=", 1)
            payload[key.strip()] = value.strip()

        return payload or None

    async def listen(self):
        self.serial_conn = serial.Serial(
            self.port,
            self.baudrate,
            timeout=self.timeout,
        )
        logger.info(f"UART subscriber connected on {self.port} @ {self.baudrate} baud")

        while True:
            try:
                raw = await asyncio.to_thread(self.serial_conn.readline)
                if not raw:
                    continue

                line = raw.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue

                payload = self._parse_line(line)
                if not payload:
                    logger.warning(f"Ignoring malformed UART line: {line}")
                    continue

                payload.setdefault("source", "uart")
                await self.aggregator.process_pubsub_event(payload)
            except Exception as e:
                logger.error(f"UART subscriber error while reading/parsing: {e}")
                await asyncio.sleep(0.5)