import asyncio
import json
import re
import time
from typing import Any

import serial

from config import Config
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
    
    def _convert_UART_payload(self, payload: str, timestamp: float) -> dict[str, Any]:
        logger.debug(f"Converting UART payload: {payload}")
        detected_class = None
        state = 'NORMAL'
        status = 'ON'
        if payload == '10000000':
            logger.warn('Received UART payload: no detections')
            return None
        elif payload == '10000001':
            logger.info('Received UART payload: detected P')
            detected_class = 'Pequena'
        elif payload == '10000010':
            logger.info('Received UART payload: detected M')
            detected_class = 'Media'
        elif payload == '10000011':
            logger.info('Received UART payload: detected G')
            detected_class = 'Grande'
        elif payload == '01000000' or payload == '01010000':
            logger.info('Received UART payload: emergency state')
            state = 'EMERGENCY'
        elif payload == '00100000':
            logger.info('Received UART payload: system offline')
            status = 'OFF'
        else:
            logger.warning(f"Received UART payload with unknown format: {payload}")
            return None
        return {
            "source": "uart",
            "class": detected_class,
            "system": state,
            "status": status,
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
            timeout=min(self.timeout, 0.05),
        )
        logger.info(f"UART subscriber connected on {self.port} @ {self.baudrate} baud")
        rx_frame = bytearray()
        last_rx_time = None
        while True:
            try:
                now = time.time()
                chunk = await asyncio.to_thread(self.serial_conn.read, self.serial_conn.in_waiting or 1)
                if chunk:
                    logger.debug(f"Raw UART chunk received: {chunk}")
                    rx_frame.extend(chunk)
                    last_rx_time = now
                    continue
                # Fecha um frame quando houve silencio suficiente entre bytes recebidos.
                if not rx_frame or last_rx_time is None or (now - last_rx_time) < FRAME_GAP_S:
                    continue

                raw_frame = bytes(rx_frame)
                logger.debug(f"Raw UART frame received: {raw_frame}")
                line = raw_frame.decode("utf-8", errors="ignore").strip()
                logger.debug(f"Decoded UART frame: {line}")
                rx_frame.clear()
                last_rx_time = None

                if not line:
                    logger.warning("Ignoring empty UART frame after decoding.")
                    continue
                
                # payload = self._parse_line(line)
                # if not payload:
                #     logger.warning(f"Ignoring malformed UART line: {line}")
                #     continue
                # payload.setdefault("source", "uart")

                event_payload = self._convert_UART_payload(line, now)
                logger.info(f"Transformed UART payload: {event_payload}")
                if event_payload:
                    await self.aggregator.process_uart_event(event_payload)
                else:
                    logger.warning(f"UART line could not be converted to event payload: {line}, skipping.")
            except Exception as e:
                logger.error(f"UART subscriber error while reading/parsing: {e}")
                await asyncio.sleep(0.5)

class UARTPublisher:
    def __init__(self, port: str, baudrate: int, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None

    def publish(self, payload: str):
        try:
            if not self.serial_conn:
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
                logger.info(f"UART publisher connected on {self.port} @ {self.baudrate} baud")
            self.serial_conn.write(payload.encode("utf-8"))
            logger.debug(f"Published to UART: {payload}")
            return True
        except Exception as e:
            logger.error(f"Error publishing to UART: {e}")
            return False

    @staticmethod
    def resolve_command_payload(operation: str, command: str) -> str | None:
        normalized_operation = str(operation or "").strip().lower()
        normalized_command = str(command or "").strip().upper()

        if re.fullmatch(r"[01]{8}", normalized_command):
            return normalized_command

        return Config.UART_COMMAND_ENCODINGS.get((normalized_operation, normalized_command))

    def publish_command(self, operation: str, command: str) -> bool:
        payload = self.resolve_command_payload(operation, command)
        if payload is None:
            logger.warning(
                "Unsupported UART command mapping for "
                f"operation='{operation}' and command='{command}'"
            )
            return False

        return self.publish(payload)
