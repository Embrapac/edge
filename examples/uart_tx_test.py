import serial
import time

# Instancia a conexão com o RPi5 (ajuste '/tmp/ttyMCU' para a sua porta real ou virtual)
mcu_port = serial.Serial('/dev/ttyAMA0', baudrate=9600, timeout=1)
time.sleep(2) # Aguarda 2 segundos para estabilizar a conexão ao abrir a porta

byte_data = b'00001100'
mcu_port.write(byte_data)

# Fecha a porta quando terminar
mcu_port.close()