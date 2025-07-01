
#!/usr/bin/env python3
"""
ZE08-CH2O Formaldehyde Sensor Test Code for Raspberry Pi
Based on official Winsen ZE08-CH2O documentation v1.7

This sensor has two modes:
1. Active Upload Mode (default): Sensor sends data every second automatically
2. Q&A Mode: Send commands to request readings

Connection:
- Pin1: Reserved
- Pin2: DAC (0.4~2V analog output)
- Pin3: GND
- Pin4: Vin (3.7V~5.5V power input)
- Pin5: UART RXD (connect to RPi TX)
- Pin6: UART TXD (connect to RPi RX)
- Pin7: Reserved
"""

import serial
import time

class ZE08_CH2O:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600):
        """
        Initialize the ZE08-CH2O sensor
        
        Args:
            port: Serial port (default: /dev/ttyUSB0)
            baudrate: Communication speed (9600 baud as per manual)
        """
        try:
            self.ser = serial.Serial(port, baudrate, timeout=2)
            print(f"Connected to ZE08-CH2O on {port}")
            print("Sensor warming up (3 minutes required)...")
            time.sleep(1)  # Brief pause after connection
        except Exception as e:
            print(f"Error connecting to sensor: {e}")
            self.ser = None
    
    def calculate_checksum(self, data):
        """
        Calculate checksum as per manual: ~(Byte1+Byte2+...Byte7) + 1
        
        Args:
            data: List of bytes (excluding start byte and checksum)
            
        Returns:
            int: Calculated checksum
        """
        checksum = sum(data) & 0xFF
        return ((~checksum) + 1) & 0xFF
    
    def switch_to_active_mode(self):
        """
        Switch sensor to active upload mode (sends data every second)
        Command: 0xFF 0x01 0x78 0x40 0x00 0x00 0x00 0x00 0x47
        """
        if not self.ser:
            return False
        
        try:
            command = bytearray([0xFF, 0x01, 0x78, 0x40, 0x00, 0x00, 0x00, 0x00])
            checksum = self.calculate_checksum(command[1:8])
            command.append(checksum)
            
            self.ser.write(command)
            print("Switched to active upload mode")
            time.sleep(0.5)
            return True
            
        except Exception as e:
            print(f"Error switching to active mode: {e}")
            return False
    
    def switch_to_qa_mode(self):
        """
        Switch sensor to Q&A mode (request/response)
        Command: 0xFF 0x01 0x78 0x41 0x00 0x00 0x00 0x00 0x46
        """
        if not self.ser:
            return False
        
        try:
            command = bytearray([0xFF, 0x01, 0x78, 0x41, 0x00, 0x00, 0x00, 0x00])
            checksum = self.calculate_checksum(command[1:8])
            command.append(checksum)
            
            self.ser.write(command)
            print("Switched to Q&A mode")
            time.sleep(0.5)
            return True
            
        except Exception as e:
            print(f"Error switching to Q&A mode: {e}")
            return False
    
    def read_concentration_qa(self):
        """
        Read concentration in Q&A mode
        Command: 0xFF 0x01 0x86 0x00 0x00 0x00 0x00 0x00 0x79
        
        Returns:
            dict: Contains ppb, ppm, and mg/m3 values, or None if error
        """
        if not self.ser:
            return None
        
        try:
            # Send read command
            command = bytearray([0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00])
            checksum = self.calculate_checksum(command[1:8])
            command.append(checksum)
            
            self.ser.write(command)
            time.sleep(0.2)
            
            # Read response (9 bytes)
            if self.ser.in_waiting >= 9:
                response = self.ser.read(9)
                
                if len(response) == 9 and response[0] == 0xFF and response[1] == 0x86:
                    # Extract ug/m3 concentration (bytes 2-3)
                    ug_m3_high = response[2]
                    ug_m3_low = response[3]
                    ug_m3 = (ug_m3_high << 8) | ug_m3_low


                    # Extract ppb concentration (bytes 6-7)
                    ppb_high = response[6]
                    ppb_low = response[7]
                    ppb = (ppb_high << 8) | ppb_low
                    
                    # Convert to different units
                    ppm = ppb / 1000.0
                    mg_m3 = ppm * 1.25  # As per manual: 1PPM × 1.25 = 1.25mg/m3
                    
                    return {
                        'ppb': ppb,
                        'ppm': ppm,
                        'mg_m3': mg_m3,
                        'ug_m3': ug_m3
                    }
                else:
                    print("Invalid response format in Q&A mode")
                    return None
            else:
                print("No response from sensor in Q&A mode")
                return None
                
        except Exception as e:
            print(f"Error reading concentration in Q&A mode: {e}")
            return None
    
    def read_active_mode(self):
        """
        Read data in active upload mode (sensor sends data automatically)
        Expected format: 0xFF 0x17 0x04 0x00 [conc_high] [conc_low] [range_high] [range_low] [checksum]
        
        Returns:
            dict: Contains ppb, ppm, and mg/m3 values, or None if error
        """
        if not self.ser:
            return None
        
        try:
            # Clear buffer first
            self.ser.reset_input_buffer()
            
            # Wait for data (sensor sends every second)
            start_time = time.time()
            while time.time() - start_time < 3:  # Wait up to 3 seconds
                if self.ser.in_waiting >= 9:
                    response = self.ser.read(9)
                    
                    if len(response) == 9 and response[0] == 0xFF and response[1] == 0x17:
                        # Validate unit is ppb (0x04 = ppb)
                        if response[2] == 0x04:
                            # Extract concentration (bytes 4-5)
                            conc_high = response[4]
                            conc_low = response[5]
                            ppb = (conc_high << 8) | conc_low
                            
                            # Convert to other units
                            ppm = ppb / 1000.0
                            mg_m3 = ppm * 1.25  # As per manual
                            
                            return {
                                'ppb': ppb,
                                'ppm': ppm,
                                'mg_m3': mg_m3
                            }
                        else:
                            print(f"Unexpected unit in response: {response[2]:02X}")
                    
                time.sleep(0.1)
            
            print("No valid data received in active mode")
            return None
            
        except Exception as e:
            print(f"Error reading active mode: {e}")
            return None
    
    def get_air_quality_level(self, mg_m3):
        """
        Get air quality level based on formaldehyde concentration
        
        Args:
            mg_m3: Concentration in mg/m³
            
        Returns:
            str: Air quality level description
        """
        if mg_m3 < 0.08:
            return "Excellent (< 0.08 mg/m³)"
        elif mg_m3 < 0.1:
            return "Good (0.08-0.1 mg/m³)"
        elif mg_m3 < 0.12:
            return "Moderate (0.1-0.12 mg/m³)"
        elif mg_m3 < 0.16:
            return "Poor (0.12-0.16 mg/m³)"
        else:
            return "Hazardous (> 0.16 mg/m³)"
    
    def close(self):
        """Close serial connection"""
        if self.ser:
            self.ser.close()
            print("Serial connection closed")



def main():
    """Main test function"""
    print("ZE08-CH2O Formaldehyde Sensor Test")
    print("Based on Official Winsen Documentation v1.7")
    print("=" * 50)
    
    # Initialize sensor
    # Common ports: /dev/ttyUSB0, /dev/ttyAMA0, /dev/serial0
    sensor = ZE08_CH2O(port='/dev/ttyUSB0', baudrate=9600)
    
    if not sensor.ser:
        print("Failed to initialize sensor. Check connections and port.")
        return
    
    try:
        print("\nChoose operation mode:")
        print("1. Active Mode (sensor sends data automatically)")
        print("2. Q&A Mode (request/response)")
        
        mode = input("Enter choice (1 or 2, default=1): ").strip()
        
        if mode == "2":
            print("\nSwitching to Q&A mode...")
            sensor.switch_to_qa_mode()
            time.sleep(1)
            
            print("Reading formaldehyde concentration in Q&A mode...")
            print("Press Ctrl+C to stop\n")
            
            while True:
                data = sensor.read_concentration_qa()
                
                if data:
                    print(f"CH2O Concentration:")
                    print(f"  {data['ppb']:.0f} ppb")
                    print(f"  {data['ppm']:.3f} ppm")
                    print(f"  {data['mg_m3']:.3f} mg/m³")
                    print(f"  {data['ug_m3']:.0f} µg/m³")
                    print(f"Air Quality: {sensor.get_air_quality_level(data['mg_m3'])}")
                else:
                    print("Failed to read sensor data")
                
                print("-" * 40)
                time.sleep(3)  # Read every 3 seconds in Q&A mode
        
        else:
            print("\nUsing Active Upload mode (default)...")
            sensor.switch_to_active_mode()
            time.sleep(1)
            
            print("Reading formaldehyde concentration in Active mode...")
            print("Sensor sends data every second automatically")
            print("Press Ctrl+C to stop\n")
            
            while True:
                data = sensor.read_active_mode()
                
                if data:
                    print(f"CH2O Concentration:")
                    print(f"  {data['ppb']:.0f} ppb")
                    print(f"  {data['ppm']:.3f} ppm")
                    print(f"  {data['mg_m3']:.3f} mg/m³")
                    print(f"Air Quality: {sensor.get_air_quality_level(data['mg_m3'])}")
                else:
                    print("Failed to read sensor data")
                
                print("-" * 40)
                time.sleep(1)  # Data comes every second in active mode
            
    except KeyboardInterrupt:
        print("\nStopping sensor readings...")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        sensor.close()

if __name__ == "__main__":
    main()
