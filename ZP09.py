#!/usr/bin/env python3
"""
ZP09 Particulate Matter Sensor Test for Raspberry Pi 4 (Direct Connection)
Reads PM2.5 concentration data from ZP09 sensor connected directly to Pi

Direct Hardware connections:
- ZP09 5V -> 5V (Pin 2 or 4)
- ZP09 GND -> GND (Pin 6)
- ZP09 A -> GPIO 15 (Pin 10) - RX on Pi
- ZP09 B -> GND (Pin 6) - Reference/Common

Alternative wiring if A/B are differential:
- ZP09 A -> GPIO 15 (Pin 10) - RX on Pi
- ZP09 B -> GPIO 14 (Pin 8) - TX on Pi (or leave disconnected)
"""

import serial
import time
import struct
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ZP09DirectSensor:
    def __init__(self, port='/dev/ttyS0', baudrate=9600, timeout=3):
        """
        Initialize ZP09 sensor direct communication
        
        Args:
            port (str): Serial port (default: /dev/ttyS0 for Pi 4)
            baudrate (int): Communication speed
            timeout (float): Read timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        
        # Common baud rates for ZP09 variants
        self.baud_rates = [9600, 2400, 4800, 19200, 38400]
        
    def connect(self, auto_detect_baud=True):
        """
        Establish serial connection to ZP09 sensor
        
        Args:
            auto_detect_baud (bool): Try different baud rates automatically
        """
        if auto_detect_baud:
            for baud in self.baud_rates:
                logger.info(f"Trying baud rate: {baud}")
                if self._try_connection(baud):
                    self.baudrate = baud
                    logger.info(f"✓ Connected at {baud} baud")
                    return True
            logger.error("Failed to connect at any baud rate")
            return False
        else:
            return self._try_connection(self.baudrate)
    
    def _try_connection(self, baudrate):
        """Try connection at specific baud rate"""
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
                
            self.ser = serial.Serial(
                port=self.port,
                baudrate=baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            
            # Test if we can read valid data
            time.sleep(1)  # Wait for sensor to settle
            test_data = self.read_data()
            if test_data:
                return True
            else:
                return False
                
        except serial.SerialException as e:
            logger.debug(f"Connection failed at {baudrate}: {e}")
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Disconnected from ZP09")
    
    def read_data(self):
        """
        Read PM data from ZP09 sensor
        
        ZP09 protocol variations supported:
        1. Standard PM sensor protocol (42 4D header)
        2. Simple ASCII format
        3. Binary format with different headers
        
        Returns:
            dict: PM concentration data or None if error
        """
        if not self.ser or not self.ser.is_open:
            logger.error("Serial connection not established")
            return None
        
        try:
            # Clear input buffer
            self.ser.flushInput()
            time.sleep(0.1)
            
            # Try different parsing methods
            for attempt in range(3):
                data = self._read_raw_data()
                if data:
                    # Try standard PM sensor protocol first
                    result = self._parse_standard_format(data)
                    if result:
                        return result
                    
                    # Try simple format
                    result = self._parse_simple_format(data)
                    if result:
                        return result
                
                time.sleep(0.5)
            
            return None
            
        except Exception as e:
            logger.error(f"Error reading data: {e}")
            return None
    
    def _read_raw_data(self):
        """Read raw data from serial port"""
        try:
            # Wait for data
            start_time = time.time()
            while self.ser.in_waiting < 2 and (time.time() - start_time) < self.timeout:
                time.sleep(0.1)
            
            if self.ser.in_waiting == 0:
                return None
            
            # Read available data
            data = self.ser.read(self.ser.in_waiting)
            
            # Try to read more if frame seems incomplete
            if len(data) < 32:
                time.sleep(0.2)
                additional = self.ser.read(self.ser.in_waiting)
                data += additional
            
            return data
            
        except Exception as e:
            logger.debug(f"Error reading raw data: {e}")
            return None
    
    def _parse_standard_format(self, data):
        """Parse standard PM sensor format (42 4D header)"""
        try:
            # Look for standard header
            for i in range(len(data) - 1):
                if data[i] == 0x42 and data[i + 1] == 0x4D:
                    # Found header, try to parse
                    if i + 32 <= len(data):
                        frame = data[i:i + 32]
                        return self._extract_pm_values(frame)
            return None
        except Exception as e:
            logger.debug(f"Error parsing standard format: {e}")
            return None
    
    def _parse_simple_format(self, data):
        """Parse simple ASCII or basic binary format"""
        try:
            # Try ASCII format first
            try:
                text = data.decode('ascii', errors='ignore')
                # Look for numbers that could be PM values
                import re
                numbers = re.findall(r'\d+', text)
                if len(numbers) >= 1:
                    pm25 = int(numbers[0])
                    if 0 <= pm25 <= 9999:  # Reasonable PM2.5 range
                        return {
                            'pm25': pm25,
                            'pm10': int(numbers[1]) if len(numbers) > 1 else pm25,
                            'pm100': int(numbers[2]) if len(numbers) > 2 else pm25,
                            'timestamp': time.time(),
                            'format': 'ascii'
                        }
            except:
                pass
            
            # Try simple binary format
            if len(data) >= 4:
                # Try different byte positions for PM2.5 value
                for offset in [0, 2, 4, 6, 8, 10]:
                    if offset + 2 <= len(data):
                        try:
                            pm25 = struct.unpack('>H', data[offset:offset + 2])[0]
                            if 0 <= pm25 <= 9999:
                                return {
                                    'pm25': pm25,
                                    'pm10': pm25,
                                    'pm100': pm25,
                                    'timestamp': time.time(),
                                    'format': 'binary_simple'
                                }
                        except:
                            continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Error parsing simple format: {e}")
            return None
    
    def _extract_pm_values(self, frame):
        """Extract PM values from standard 32-byte frame"""
        try:
            # Verify frame length
            if len(frame) < 32:
                return None
            
            # Check frame length field
            frame_length = struct.unpack('>H', frame[2:4])[0]
            
            # Extract PM values at standard positions
            pm10_cf1 = struct.unpack('>H', frame[4:6])[0]
            pm25_cf1 = struct.unpack('>H', frame[6:8])[0]
            pm100_cf1 = struct.unpack('>H', frame[8:10])[0]
            
            pm10_atm = struct.unpack('>H', frame[10:12])[0]
            pm25_atm = struct.unpack('>H', frame[12:14])[0]
            pm100_atm = struct.unpack('>H', frame[14:16])[0]
            
            # Use atmospheric values if available, otherwise CF=1 values
            pm25 = pm25_atm if pm25_atm > 0 else pm25_cf1
            pm10 = pm10_atm if pm10_atm > 0 else pm10_cf1
            pm100 = pm100_atm if pm100_atm > 0 else pm100_cf1
            
            # Sanity check values
            if 0 <= pm25 <= 9999 and 0 <= pm10 <= 9999:
                return {
                    'pm25': pm25,
                    'pm10': pm10,
                    'pm100': pm100,
                    'pm25_cf1': pm25_cf1,
                    'pm10_cf1': pm10_cf1,
                    'pm100_cf1': pm100_cf1,
                    'timestamp': time.time(),
                    'format': 'standard'
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting PM values: {e}")
            return None
    
    def test_sensor(self, duration=60, interval=5):
        """
        Test sensor by reading data for specified duration
        
        Args:
            duration (int): Test duration in seconds
            interval (int): Reading interval in seconds
        """
        logger.info(f"Starting ZP09 test for {duration} seconds")
        
        start_time = time.time()
        readings = []
        
        try:
            while time.time() - start_time < duration:
                data = self.read_data()
                
                if data:
                    readings.append(data)
                    format_info = f" [{data.get('format', 'unknown')}]"
                    logger.info(f"PM2.5: {data['pm25']} μg/m³{format_info}")
                    print(f"PM2.5: {data['pm25']} μg/m³ | PM10: {data['pm10']} μg/m³{format_info}")
                else:
                    logger.warning("Failed to read data")
                    print("No valid data received")
                
                time.sleep(interval)
            
            # Calculate statistics
            if readings:
                pm25_values = [r['pm25'] for r in readings]
                avg_pm25 = sum(pm25_values) / len(pm25_values)
                min_pm25 = min(pm25_values)
                max_pm25 = max(pm25_values)
                
                print(f"\n--- Test Results ---")
                print(f"Total readings: {len(readings)}")
                print(f"Baud rate used: {self.baudrate}")
                print(f"PM2.5 - Avg: {avg_pm25:.2f} μg/m³, Min: {min_pm25} μg/m³, Max: {max_pm25} μg/m³")
                
                return True
            else:
                logger.error("No valid readings obtained")
                return False
                
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
            return False

def setup_raspberry_pi():
    """Setup Raspberry Pi for ZP09 direct connection"""
    print("ZP09 Direct Connection Setup:")
    print("1. Enable UART: sudo raspi-config -> Interface Options -> Serial")
    print("2. Disable serial console, enable serial hardware")
    print("3. Add 'enable_uart=1' to /boot/config.txt")
    print("4. Reboot the Pi")
    print("\nDirect Hardware Connections (Method 1 - Single-ended):")
    print("ZP09 5V -> Pi Pin 2 (5V)")
    print("ZP09 GND -> Pi Pin 6 (GND)")
    print("ZP09 A -> Pi Pin 10 (GPIO 15/RX)")
    print("ZP09 B -> Pi Pin 6 (GND) - Common reference")
    print("\nAlternative (Method 2 - If differential):")
    print("ZP09 A -> Pi Pin 10 (GPIO 15/RX)")
    print("ZP09 B -> Leave disconnected or try Pin 8 (GPIO 14/TX)")
    print("-" * 50)

def debug_raw_data(sensor, duration=10):
    """Debug function to show raw data from sensor"""
    print(f"\n--- Debug Mode: Raw Data for {duration} seconds ---")
    
    if not sensor.ser or not sensor.ser.is_open:
        print("Sensor not connected")
        return
    
    start_time = time.time()
    while time.time() - start_time < duration:
        sensor.ser.flushInput()
        time.sleep(0.5)
        
        if sensor.ser.in_waiting > 0:
            raw_data = sensor.ser.read(sensor.ser.in_waiting)
            print(f"Raw bytes ({len(raw_data)}): {' '.join([f'{b:02X}' for b in raw_data])}")
            
            # Try to decode as ASCII
            try:
                ascii_data = raw_data.decode('ascii', errors='ignore')
                if ascii_data.strip():
                    print(f"ASCII: '{ascii_data.strip()}'")
            except:
                pass
        else:
            print("No data received")
        
        time.sleep(1)

def main():
    """Main test function"""
    setup_raspberry_pi()
    
    # Initialize sensor
    sensor = ZP09DirectSensor(port='/dev/ttyS0')
    
    print("Starting ZP09 direct connection tests...\n")
    
    # Test connectivity with auto baud detection
    print("1. Testing connection with auto baud detection...")
    if sensor.connect(auto_detect_baud=True):
        print(f"✓ Connected successfully at {sensor.baudrate} baud")
        
        # Single reading test
        print("\n2. Testing single reading...")
        data = sensor.read_data()
        if data:
            print(f"✓ PM2.5: {data['pm25']} μg/m³ (format: {data.get('format', 'unknown')})")
        else:
            print("- No valid data, starting debug mode...")
            debug_raw_data(sensor, duration=10)
    else:
        print("✗ Connection failed")
        print("Troubleshooting:")
        print("- Check 5V power connection")
        print("- Try swapping A and B connections")
        print("- Verify UART is enabled")
        print("- Check if sensor needs warm-up time")
        return
    
    # Continuous monitoring test
    print("\n3. Starting continuous monitoring (60 seconds)...")
    print("Press Ctrl+C to stop early\n")
    
    success = sensor.test_sensor(duration=60, interval=5)
    
    if success:
        print("\n✓ ZP09 sensor test completed successfully!")
    else:
        print("\n✗ ZP09 sensor test failed")
        print("\nTrying debug mode to see raw data...")
        debug_raw_data(sensor, duration=15)
    
    sensor.disconnect()

if __name__ == "__main__":
    main()
