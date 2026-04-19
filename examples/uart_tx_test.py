import argparse
import serial
import time

parser = argparse.ArgumentParser(description='Envia dados para a UART do MCU.')
parser.add_argument('byte_data', help='Valor a enviar, por exemplo: 00001100')
args = parser.parse_args()

# Instancia a conexão com o RPi5 (ajuste '/tmp/ttyMCU' para a sua porta real ou virtual)
mcu_port = serial.Serial('/dev/ttyAMA0', baudrate=9600, timeout=1)
time.sleep(2)  # Aguarda 2 segundos para estabilizar a conexão ao abrir a porta

byte_data = args.byte_data.encode('utf-8')
mcu_port.write(byte_data)

# Fecha a porta quando terminar
mcu_port.close()