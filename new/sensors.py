#!/usr/bin/env python3
"""
ZH07 Laser Dust Sensor Test Script

This script communicates with the ZH07 laser dust sensor via UART/serial interface
to read PM1.0, PM2.5, and PM10 values.

Hardware connections:
- VCC: 5V
- GND: Ground
- TX: Connect to RX pin of microcontroller/USB-to-serial
- RX: Connect to TX pin of microcontroller/USB-to-serial

Default serial settings: 9600 baud, 8N1
"""

import serial
import time
import struct
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ZH07Sensor:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600, timeout=2):
        """
        Initialize ZH07 sensor
        
        Args:
            port (str): Serial port path (e.g., '/dev/ttyUSB0' on Linux, 'COM3' on Windows)
            baudrate (int): Serial communication baud rate (default: 9600)
            timeout (float): Serial read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn = None
        
        # ZH07 command constants
        self.CMD_READ_DATA = b'\xFF\x01\x86\x00\x00\x00\x00\x00\x79'
        self.CMD_SLEEP = b'\xFF\x01\xA7\x01\x00\x00\x00\x00\x57'
        self.CMD_WAKEUP = b'\xFF\x01\xA7\x00\x00\x00\x00\x00\x58'
        
    def connect(self):
        """Establish serial connection to the sensor"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            logger.info(f"Connected to ZH07 sensor on {self.port}")
            time.sleep(2)  # Wait for sensor to stabilize
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to connect to sensor: {e}")
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("Disconnected from sensor")
    
    def calculate_checksum(self, data):
        """Calculate checksum for ZH07 commands"""
        return (0xFF - sum(data[1:8])) & 0xFF
    
    def read_data(self):
        """
        Read PM data from the sensor
        
        Returns:
            dict: Dictionary containing PM1.0, PM2.5, PM10 values in µg/m³
                  Returns None if reading fails
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            logger.error("Serial connection not established")
            return None
        
        try:
            # Clear input buffer
            self.serial_conn.flushInput()
            
            # Send read command
            self.serial_conn.write(self.CMD_READ_DATA)
            logger.debug(f"Sent command: {self.CMD_READ_DATA.hex()}")
            
            # Wait a bit for response
            time.sleep(0.1)
            
            # Read response (9 bytes expected)
            response = self.serial_conn.read(9)
            
            if len(response) == 0:
                logger.warning("No response from sensor")
                return None
            
            logger.debug(f"Received {len(response)} bytes: {response.hex()}")
            
            if len(response) != 9:
                logger.warning(f"Incomplete response: {len(response)} bytes received")
                # Try to read more data if available
                additional_data = self.serial_conn.read(20)
                if additional_data:
                    logger.debug(f"Additional data: {additional_data.hex()}")
                return None
            
            # Parse response - check for different header formats
            if response[0] == 0xFF and response[1] == 0x86:
                # Standard ZH07 response format
                logger.debug("Standard ZH07 format detected")
                pm1_0 = struct.unpack('>H', response[2:4])[0]
                pm2_5 = struct.unpack('>H', response[4:6])[0]
                pm10 = struct.unpack('>H', response[6:8])[0]
                
                # Verify checksum
                checksum = response[8]
                calculated_checksum = self.calculate_checksum(response)
                
                if checksum != calculated_checksum:
                    logger.warning(f"Checksum mismatch: got {checksum:02x}, expected {calculated_checksum:02x}")
                    return None
                
            elif response[0] == 0x42 and response[1] == 0x4D:
                # Alternative format (some ZH07 variants use PMS-like protocol)
                logger.debug("PMS-like format detected")
                frame_length = struct.unpack('>H', response[2:4])[0]
                if frame_length != 20:
                    logger.warning(f"Unexpected frame length: {frame_length}")
                
                # Read the rest of the frame
                additional_response = self.serial_conn.read(frame_length + 4 - 9)
                if len(additional_response) != frame_length + 4 - 9:
                    logger.warning("Could not read complete frame")
                    return None
                
                full_response = response + additional_response
                logger.debug(f"Full frame: {full_response.hex()}")
                
                # Extract PM values from PMS-like format
                pm1_0 = struct.unpack('>H', full_response[10:12])[0]
                pm2_5 = struct.unpack('>H', full_response[12:14])[0]
                pm10 = struct.unpack('>H', full_response[14:16])[0]
                
            else:
                logger.warning(f"Unknown response format: {response[0]:02x} {response[1]:02x}")
                logger.debug(f"Full response: {response.hex()}")
                return None
            
            return {
                'PM1.0': pm1_0,
                'PM2.5': pm2_5,
                'PM10': pm10,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Error reading data: {e}")
            return None
    
    def sleep(self):
        """Put sensor into sleep mode"""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.write(self.CMD_SLEEP)
            logger.info("Sensor put to sleep")
    
    def read_passive_data(self):
        """
        Try to read data in passive mode (without sending commands)
        Some ZH07 variants continuously send data
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            logger.error("Serial connection not established")
            return None
        
        try:
            # Clear input buffer and wait for incoming data
            self.serial_conn.flushInput()
            time.sleep(1)
            
            # Read available data
            available_bytes = self.serial_conn.in_waiting
            if available_bytes > 0:
                data = self.serial_conn.read(available_bytes)
                logger.debug(f"Passive mode: received {len(data)} bytes: {data.hex()}")
                
                # Look for frame headers
                for i in range(len(data) - 8):
                    if data[i] == 0xFF and data[i+1] == 0x86 and i + 8 < len(data):
                        # Found standard ZH07 frame
                        frame = data[i:i+9]
                        logger.debug(f"Found standard frame: {frame.hex()}")
                        return self.parse_standard_frame(frame)
                    elif data[i] == 0x42 and data[i+1] == 0x4D and i + 23 < len(data):
                        # Found PMS-like frame
                        frame = data[i:i+24]
                        logger.debug(f"Found PMS-like frame: {frame.hex()}")
                        return self.parse_pms_frame(frame)
            
            return None
            
        except Exception as e:
            logger.error(f"Error reading passive data: {e}")
            return None
    
    def parse_standard_frame(self, frame):
        """Parse standard ZH07 frame format"""
        try:
            pm1_0 = struct.unpack('>H', frame[2:4])[0]
            pm2_5 = struct.unpack('>H', frame[4:6])[0]
            pm10 = struct.unpack('>H', frame[6:8])[0]
            
            # Verify checksum
            checksum = frame[8]
            calculated_checksum = self.calculate_checksum(frame)
            
            if checksum != calculated_checksum:
                logger.warning(f"Checksum mismatch: got {checksum:02x}, expected {calculated_checksum:02x}")
                return None
            
            return {
                'PM1.0': pm1_0,
                'PM2.5': pm2_5,
                'PM10': pm10,
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"Error parsing standard frame: {e}")
            return None
    
    def parse_pms_frame(self, frame):
        """Parse PMS-like frame format"""
        try:
            # Extract PM values from PMS-like format
            pm1_0 = struct.unpack('>H', frame[10:12])[0]
            pm2_5 = struct.unpack('>H', frame[12:14])[0]
            pm10 = struct.unpack('>H', frame[14:16])[0]
            
            return {
                'PM1.0': pm1_0,
                'PM2.5': pm2_5,
                'PM10': pm10,
                'timestamp': time.time()
            }
        except Exception as e:
            logger.error(f"Error parsing PMS frame: {e}")
            return None

def main():
    """Main test function"""
    # Configuration
    SERIAL_PORT = '/dev/ttyUSB0'  # Change this to your serial port
    # For Windows, use something like 'COM3'
    # For macOS, use something like '/dev/tty.usbserial-xxxxx'
    
    # Initialize sensor
    sensor = ZH07Sensor(port=SERIAL_PORT)
    
    try:
        # Connect to sensor
        if not sensor.connect():
            logger.error("Failed to connect to sensor. Check connection and port.")
            return
        
        # Wake up sensor (in case it's sleeping)
        sensor.wakeup()
        
        logger.info("Starting continuous measurement...")
        logger.info("Press Ctrl+C to stop")
        
        # Continuous measurement loop
        measurement_count = 0
        while True:
            data = sensor.read_data()
            
            if data:
                measurement_count += 1
                print(f"\n--- Measurement #{measurement_count} ---")
                print(f"PM1.0: {data['PM1.0']} µg/m³")
                print(f"PM2.5: {data['PM2.5']} µg/m³")
                print(f"PM10:  {data['PM10']} µg/m³")
                print(f"Time:  {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['timestamp']))}")
                
                # Air quality assessment
                pm2_5_level = data['PM2.5']
                if pm2_5_level <= 12:
                    quality = "Good"
                elif pm2_5_level <= 35:
                    quality = "Moderate"
                elif pm2_5_level <= 55:
                    quality = "Unhealthy for Sensitive Groups"
                elif pm2_5_level <= 150:
                    quality = "Unhealthy"
                elif pm2_5_level <= 250:
                    quality = "Very Unhealthy"
                else:
                    quality = "Hazardous"
                
                print(f"Air Quality: {quality}")
                
            else:
                logger.warning("Failed to read data")
            
            # Wait before next measurement
            time.sleep(5)
    
    except KeyboardInterrupt:
        logger.info("Measurement stopped by user")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    
    finally:
        # Clean up
        sensor.disconnect()
        logger.info("Test completed")

def test_single_measurement():
    """Test function for single measurement"""
    sensor = ZH07Sensor(port='/dev/ttyUSB0')  # Adjust port as needed
    
    if sensor.connect():
        sensor.wakeup()
        time.sleep(3)  # Wait for sensor to stabilize
        
        data = sensor.read_data()
        if data:
            print("Single measurement:")
            print(f"PM1.0: {data['PM1.0']} µg/m³")
            print(f"PM2.5: {data['PM2.5']} µg/m³")
            print(f"PM10: {data['PM10']} µg/m³")
        else:
            print("Failed to read data")
        
        sensor.disconnect()

if __name__ == "__main__":
    # Choose test mode
    print("ZH07 Sensor Test Options:")
    print("1. Continuous measurement (default)")
    print("2. Single measurement")
    print("3. Passive mode test")
    print("4. Raw data debugging")
    
    choice = input("Enter choice (1-4) or press Enter for default: ").strip()
    
    if choice == "2":
        test_single_measurement()
    elif choice == "3":
        test_passive_mode()
    elif choice == "4":
        debug_raw_data()
    else:
        # Run continuous measurement (default)
        main()
