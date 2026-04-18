import asyncio
import json
import time
from typing import Any

import serial

from shared.logger import get_struct_logger

logger = get_struct_logger(__name__)

def bytes_to_bin_msb(data: bytes) -> str:
    return " ".join(f"{b:08b}" for b in data)

def calc_char_time_s(baud, bytesize, parity, stopbits):
    parity_bits = 0 if parity == serial.PARITY_NONE else 1
    stop_bits = 1.0 if stopbits == serial.STOPBITS_ONE else 2.0
    total_bits = 1.0 + bytesize + parity_bits + stop_bits
    return total_bits / float(baud)


BYTESIZE = serial.EIGHTBITS
PARITY = serial.PARITY_NONE
STOPBITS = serial.STOPBITS_ONE
CHAR_TIME_S = calc_char_time_s(9600, 8, PARITY, STOPBITS)
FRAME_GAP_S = 5.0 * CHAR_TIME_S

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
            print(f"Attempting to transform UART line as JSON: {raw_line}")
            payload = json.loads(raw_line)
            print(f"Parsed UART JSON payload: {payload}")
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
    
    def _convert_UART_payload(self, payload: dict[str, Any], timestamp: float) -> dict[str, Any]:
        logger.debug(f"Converting UART payload: {payload}")
        return {
            "source": "uart",
            "class": "Pequena",
            "timestamp": timestamp
        }

    async def listen(self):
        self.serial_conn = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            bytesize=BYTESIZE,
            parity=PARITY,
            stopbits=STOPBITS,
            inter_byte_timeout=0.01,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False,
            timeout=self.timeout,
        )
        logger.info(f"UART subscriber connected on {self.port} @ {self.baudrate} baud")
        rx_frame = bytearray()
        last_rx_time = None
        while True:
            try:
                # raw = await asyncio.to_thread(self.serial_conn.readline)
                chunk = serial.read(serial.in_waiting or 1)
                # if not raw:
                #     continue
                logger.debug(f"Raw UART line received: {raw}")
                now = time.monotonic()
                # Estado da captura RX
                if chunk:
                    rx_frame.extend(chunk)
                    last_rx_time = now
                elif rx_frame and last_rx_time is not None and (now - last_rx_time) >= FRAME_GAP_S:
                    seq += 1
                    raw = bytes(rx_frame)
                    # ts_humano = log_frame(writer, seq, "RX", raw)
                    line = bytes_to_bin_msb(raw)
                    rx_frame.clear()
                    last_rx_time = None

                # line = raw.decode("utf-8", errors="ignore").strip()
                if not line:
                    continue
                logger.debug(f"Decoded UART line: {line}")
                
                # payload = self._parse_line(line)
                # if not payload:
                #     logger.warning(f"Ignoring malformed UART line: {line}")
                #     continue
                # payload.setdefault("source", "uart")

                event_payload = self._convert_UART_payload(line, now)
                logger.info(f"Transformed UART payload: {event_payload}")

                await self.aggregator.process_pubsub_event(event_payload)
            except Exception as e:
                logger.error(f"UART subscriber error while reading/parsing: {e}")
                await asyncio.sleep(0.5)
