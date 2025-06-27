import serial
import time

ser = serial.Serial('/dev/serial0', 9600, timeout=1)

def poll_zh07(ser):
    request = bytes([0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79])
    ser.write(request)
    time.sleep(0.1)
    if ser.in_waiting >= 9:
        data = ser.read(9)
        print("Response:", data.hex())
    else:
        print("No response")

poll_zh07(ser)
