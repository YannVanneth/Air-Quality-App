import serial
ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)

while True:
        buf = ser.read(9)
        print("hello")
        if len(buf)==9 and buf[0]==0xFF and buf[1]==0x17:
            ppb = buf[5]*256 + buf[6]
            ppm = ppb / 1000.0
            print(f"HCHO = {ppm:.3f} ppm")

