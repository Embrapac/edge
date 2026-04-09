#!/usr/bin/env python3
"""Simple UART reader to validate RX on Raspberry Pi GPIO15 (UART RXD)."""

import argparse
import json
import time

import serial


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read lines from UART and optionally parse JSON payloads.",
    )
    parser.add_argument("--port", default="/dev/serial0", help="UART device path")
    parser.add_argument("--baud", type=int, default=115200, help="Baudrate")
    parser.add_argument("--timeout", type=float, default=1.0, help="Read timeout in seconds")
    parser.add_argument(
        "--raw-only",
        action="store_true",
        help="Only print raw line text (skip JSON parsing)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    print(f"Opening UART on {args.port} @ {args.baud} baud")
    with serial.Serial(args.port, args.baud, timeout=args.timeout) as uart:
        print("Connected. Waiting for data... Press Ctrl+C to stop.")
        while True:
            raw = uart.readline()
            if not raw:
                continue

            line = raw.decode("utf-8", errors="ignore").strip()
            if not line:
                continue

            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] RAW: {line}")

            if args.raw_only:
                continue

            # try:
            #     payload = json.loads(line)
            #     print(f"[{ts}] JSON: {payload}")
            # except json.JSONDecodeError:
            #     print(f"[{ts}] Not JSON payload")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped by user.")
