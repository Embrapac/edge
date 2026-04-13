#!/usr/bin/env python3
import csv
import time
import serial

PORTA = "/dev/ttyACM0"  # ajuste se necessário
BAUD = 115200
ARQUIVO_CSV = "uart_capture.csv"

def bits_lsb_first(byte_value: int) -> str:
    """Retorna os 8 bits na ordem temporal típica da UART (LSB first)."""
    return "".join(str((byte_value >> i) & 1) for i in range(8))

with serial.Serial(
    port=PORTA,
    baudrate=BAUD,
    bytesize=serial.EIGHTBITS,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    timeout=1,
    xonxoff=False,
    rtscts=False,
    dsrdtr=False,
) as ser, open(ARQUIVO_CSV, "w", newline="") as f_csv:

    writer = csv.writer(f_csv)
    writer.writerow([
        "timestamp_epoch",
        "seq",
        "byte_hex",
        "byte_bin_msb",
        "byte_bin_lsb_temporal",
        "uart_frame_reconstruido"
    ])

    print(f"Monitorando {PORTA} @ {BAUD} bps (8N1)")
    print(f"Gravando em: {ARQUIVO_CSV}")
    print("Pressione Ctrl+C para encerrar.\n")

    seq = 0

    try:
        while True:
            raw = ser.read(1)   # lê 1 byte do fluxo serial
            if not raw:
                continue

            seq += 1
            byte_value = raw[0]
            ts = time.time()

            bin_msb = f"{byte_value:08b}"
            bin_lsb = bits_lsb_first(byte_value)
            uart_frame = f"0 {bin_lsb} 1"

            writer.writerow([
                f"{ts:.6f}",
                seq,
                f"{byte_value:02X}",
                bin_msb,
                bin_lsb,
                uart_frame
            ])
            f_csv.flush()

            print(
                f"[{seq:06d}] "
                f"HEX=0x{byte_value:02X} "
                f"BIN={bin_msb} "
                f"UART={uart_frame}"
            )

    except KeyboardInterrupt:
        print("\nCaptura encerrada pelo usuário.")