import serial
import time

def checksum(data):
    return sum(data[0:8]) % 256

    # Passive mode request frame (ZH06 protocol)
REQUEST_FRAME = bytearray([0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79])

try:
    ser = serial.Serial('/dev/ttyAMA0', 9600, timeout=1)
    print("Requesting data from ZH06-I...")
except serial.SerialException as e:
    print(f"Serial error: {e}")
    exit(1)

while True:
      ser.write(REQUEST_FRAME)
      print('debug')
      time.sleep(0.1)  # Wait for sensor to respond
      data = ser.read(9)
      print(f"Raw bytes: {list(data)}") 
                                  
      if len(data) == 9 and data[0] == 0xFF and data[1] == 0x18:
         if checksum(data) == data[8]:
             pm2_5 = data[2] * 256 + data[3]
             pm10  = data[4] * 256 + data[5]
             print(f"PM2.5 = {pm2_5} µg/m³, PM10 = {pm10} µg/m³")
         else:
             print("Checksum failed")
      else:
           print("No valid response")

      time.sleep(1)
    
    
        
     
     
