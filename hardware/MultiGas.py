
import serial
import time
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
from SensorInterface import BaseSensor, SensorReading, SensorStatus, AirQualityLevel


class ZCE04BSensor(BaseSensor):
    EXPECTED_RESPONSE_LENGTH = 13
    DEFAULT_BAUD = 9600
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5
    READ_TIMEOUT = 3.0
    RESPONSE_WAIT = 0.3

    def __init__(self, port: str, sensor_id: str = "ZCE04B_001",
                 baudrate: int = DEFAULT_BAUD):
        self.port = port
        self.baudrate = baudrate
        self.sensor_id = sensor_id
        self.ser = None
        self.logger = logging.getLogger(f"{__name__}.ZCE04B")
        self.status = SensorStatus.DISCONNECTED
        self.consecutive_failures = 0
        self.last_successful_read = None

    def connect(self) -> bool:
        """Connect to the ZCE04B sensor"""
        if self.status == SensorStatus.READY:
            return True

        try:
            self.status = SensorStatus.CONNECTING
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.READ_TIMEOUT,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )

            # Wait for connection to stabilize
            time.sleep(0.5)

            # Clear any existing data
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

            self.status = SensorStatus.READY
            self.consecutive_failures = 0
            self.logger.info(f"Connected to {self.sensor_id} on {self.port}")
            return True

        except Exception as e:
            self.status = SensorStatus.ERROR
            self.logger.error(f"Connection failed: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from the sensor"""
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.status = SensorStatus.DISCONNECTED
        self.logger.info(f"Disconnected {self.sensor_id}")

    def _calculate_crc16_modbus(self, data: bytes) -> int:
        """Calculate CRC16 for Modbus RTU protocol"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def _create_modbus_frame(self, slave_id: int, function_code: int, 
                           start_reg: int, num_regs: int) -> bytearray:
        """Create a proper Modbus RTU frame"""
        frame = bytearray([
            slave_id,           # Slave address
            function_code,      # Function code
            (start_reg >> 8) & 0xFF,  # Start register high byte
            start_reg & 0xFF,   # Start register low byte
            (num_regs >> 8) & 0xFF,   # Number of registers high byte
            num_regs & 0xFF     # Number of registers low byte
        ])

        # Calculate CRC
        crc = self._calculate_crc16_modbus(frame)
        frame.append(crc & 0xFF)        # CRC low byte
        frame.append((crc >> 8) & 0xFF) # CRC high byte

        return frame

    def _send_request(self, frame: bytearray) -> Optional[bytes]:
        """Send a Modbus request and return response"""
        if not self.ser or not self.ser.is_open:
            return None

        try:
            # Clear input buffer
            self.ser.reset_input_buffer()
            
            # Send request
            self.ser.write(frame)
            self.ser.flush()
            
            # Wait for response
            time.sleep(self.RESPONSE_WAIT)
            
            # Read response
            if self.ser.in_waiting > 0:
                response = self.ser.read(self.ser.in_waiting)
                return response
            
            return None
            
        except Exception as e:
            self.logger.error(f"Communication error: {e}")
            return None

    def _validate_response(self, response: bytes, expected_slave_id: int) -> bool:
        """Validate Modbus response"""
        if not response or len(response) < 3:
            return False
            
        # Check if it's an error response
        if response[1] & 0x80:
            self.logger.error(f"Modbus error response: {response[2]}")
            return False
            
        # Basic validation
        if response[0] != expected_slave_id:
            self.logger.warning(f"Unexpected slave ID: {response[0]}")
            
        return True

    def read_sensor_data(self) -> Optional[SensorReading]:
        """Read gas sensor data from ZCE04B"""
        if self.status != SensorStatus.READY:
            if not self.connect():
                return None

        # Define frame variations to try
        frame_variations = [
            # Standard Modbus read holding registers
            (0x01, 0x03, 0x0000, 0x0004, "Read 4 holding registers from 0x0000"),
            (0x01, 0x04, 0x0000, 0x0004, "Read 4 input registers from 0x0000"),
            # ZCE04B specific variations
            (0x01, 0x03, 0x0086, 0x0001, "Read holding register 0x86"),
            (0x01, 0x04, 0x0086, 0x0001, "Read input register 0x86"),
            # Try different slave addresses
            (0xFF, 0x03, 0x0000, 0x0004, "Broadcast read holding registers"),
        ]

        for slave_id, func_code, start_reg, num_regs, description in frame_variations:
            frame = self._create_modbus_frame(slave_id, func_code, start_reg, num_regs)
            
            for retry in range(self.MAX_RETRIES):
                response = self._send_request(frame)
                
                if response and self._validate_response(response, slave_id):
                    gas_data = self._parse_gas_data(response)
                    if gas_data:
                        self.consecutive_failures = 0
                        self.last_successful_read = datetime.now()
                        
                        return SensorReading(
                            sensor_id=self.sensor_id,
                            timestamp=datetime.now(),
                            data=gas_data,
                            status=SensorStatus.READY,
                            quality=self._assess_data_quality(gas_data)
                        )
                
                time.sleep(self.RETRY_DELAY)
            
            self.logger.debug(f"Failed to get response with {description}")

        # If all variations fail
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.MAX_RETRIES:
            self.status = SensorStatus.ERROR
            
        return None

    def _parse_gas_data(self, response: bytes) -> Optional[Dict]:
        """Parse gas sensor data from response"""
        try:
            # ZCE04B typically returns data in specific format
            # This is a generic parser - adjust based on actual sensor documentation
            
            if len(response) < 7:  # Minimum expected response length
                return None
                
            # Skip slave ID and function code
            data_start = 3 if response[1] in [0x03, 0x04] else 2
            
            if len(response) < data_start + 4:
                return None
                
            # Parse gas concentrations (adjust based on actual sensor format)
            gas_data = {
                'CO': int.from_bytes(response[data_start:data_start+2], 'big'),
                'H2S': int.from_bytes(response[data_start+2:data_start+4], 'big'),
                'CH4': response[data_start+4] if len(response) > data_start+4 else 0,
                'O2': response[data_start+5] if len(response) > data_start+5 else 0,
                'temperature': response[data_start+6] if len(response) > data_start+6 else 0,
                'humidity': response[data_start+7] if len(response) > data_start+7 else 0,
                'raw_response': response.hex()
            }
            
            return gas_data
            
        except Exception as e:
            self.logger.error(f"Error parsing gas data: {e}")
            return None

    def _assess_data_quality(self, data: Dict) -> AirQualityLevel:
        """Assess air quality based on gas concentrations"""
        # Basic quality assessment - adjust thresholds based on requirements
        co_level = data.get('CO', 0)
        h2s_level = data.get('H2S', 0)
        
        if co_level > 50 or h2s_level > 10:
            return AirQualityLevel.POOR
        elif co_level > 20 or h2s_level > 5:
            return AirQualityLevel.MODERATE
        else:
            return AirQualityLevel.GOOD

    def get_status(self) -> SensorStatus:
        """Get current sensor status"""
        return self.status

    def get_last_reading_time(self) -> Optional[datetime]:
        """Get timestamp of last successful reading"""
        return self.last_successful_read


class ZCE04BSensorTester:
    """Helper class for testing and debugging ZCE04B sensor communication"""
    
    def __init__(self, port: str, baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        
    def print_hex_bytes(self, data: bytes, label: str = "Data"):
        """Helper function to print bytes in hex format"""
        hex_str = ' '.join([f'{b:02X}' for b in data])
        print(f"{label}: [{hex_str}] (Length: {len(data)})")

    def test_frame_variation(self, frame: bytearray, variation_name: str) -> Optional[bytes]:
        """Test a specific frame variation"""
        print(f"\n🧪 Testing {variation_name}")
        self.print_hex_bytes(frame, "Request frame")

        if not self.ser or not self.ser.is_open:
            print("❌ Serial port not open")
            return None

        # Clear buffer
        if self.ser.in_waiting > 0:
            old_data = self.ser.read(self.ser.in_waiting)
            print(f"⚠ Cleared {len(old_data)} bytes from buffer")

        try:
            # Send request
            bytes_written = self.ser.write(frame)
            print(f"✓ Wrote {bytes_written} bytes to serial port")
            self.ser.flush()

            # Wait for response with multiple timeouts
            for wait_time in [0.1, 0.5, 1.0, 2.0]:
                time.sleep(wait_time)
                bytes_available = self.ser.in_waiting

                if bytes_available > 0:
                    print(f"📊 Found {bytes_available} bytes after {wait_time}s wait")
                    response = self.ser.read(bytes_available)
                    self.print_hex_bytes(response, "Response")
                    return response

                print(f"⏳ No response after {wait_time}s...")

            print("✗ No response received")
            return None

        except Exception as e:
            print(f"✗ Error during communication: {e}")
            return None

    def scan_baudrates(self) -> Optional[int]:
        """Try different baudrates to find the correct one"""
        baudrates = [9600, 19200, 38400, 57600, 115200, 4800, 2400]
        
        for baud in baudrates:
            print(f"\n🔍 Testing baudrate: {baud}")
            try:
                if self.ser and self.ser.is_open:
                    self.ser.close()

                self.ser = serial.Serial(self.port, baud, timeout=1)
                
                # Create test frame
                sensor = ZCE04BSensor(self.port, baudrate=baud)
                test_frame = sensor._create_modbus_frame(0x01, 0x03, 0x0000, 0x0001)
                
                self.ser.write(test_frame)
                self.ser.flush()
                time.sleep(0.5)

                if self.ser.in_waiting > 0:
                    response = self.ser.read(self.ser.in_waiting)
                    print(f"🎯 RESPONSE FOUND at {baud} baud!")
                    self.print_hex_bytes(response, "Response")
                    return baud

            except Exception as e:
                print(f"   Error at {baud}: {e}")
                if self.ser and self.ser.is_open:
                    self.ser.close()

        return None

    def comprehensive_test(self) -> None:
        """Run comprehensive sensor test"""
        print("\n" + "="*60)
        print("🔬 COMPREHENSIVE ZCE04B SENSOR TEST")
        print("="*60)
        
        # First, try to find correct baudrate
        found_baud = self.scan_baudrates()
        if found_baud:
            self.baudrate = found_baud
            print(f"✓ Using baudrate: {self.baudrate}")
        else:
            print("⚠ No response found, using default baudrate")
            
        # Initialize sensor with found/default baudrate
        sensor = ZCE04BSensor(self.port, baudrate=self.baudrate)
        
        # Test frame variations
        frame_variations = [
            (sensor._create_modbus_frame(0x01, 0x03, 0x0000, 0x0004), "Standard Modbus Read Holding"),
            (sensor._create_modbus_frame(0x01, 0x04, 0x0000, 0x0004), "Standard Modbus Read Input"),
            (sensor._create_modbus_frame(0x01, 0x03, 0x0086, 0x0001), "ZCE04B Specific Register"),
            (sensor._create_modbus_frame(0xFF, 0x03, 0x0000, 0x0004), "Broadcast Read"),
        ]
        
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
            
            for frame, name in frame_variations:
                response = self.test_frame_variation(frame, name)
                if response and len(response) > 0:
                    print(f"🎉 SUCCESS with {name}!")
                    self.analyze_response(response)
                    break
                time.sleep(0.5)
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
        finally:
            if self.ser and self.ser.is_open:
                self.ser.close()

    def analyze_response(self, response: bytes) -> None:
        """Analyze the sensor response"""
        print(f"\n📊 RESPONSE ANALYSIS")
        print(f"Length: {len(response)} bytes")
        self.print_hex_bytes(response, "Full Response")

        if len(response) >= 2:
            print("Response breakdown:")
            print(f"  Slave ID: 0x{response[0]:02X} ({response[0]})")
            print(f"  Function Code: 0x{response[1]:02X} ({response[1]})")
            
            if response[1] & 0x80:
                print(f"  ❌ Error Code: 0x{response[2]:02X}" if len(response) > 2 else "  ❌ Error response")
            else:
                if len(response) > 2:
                    print(f"  Data Length: {response[2]}" if response[1] in [0x03, 0x04] else "  Data starts at byte 2")
                    
                    # Try to interpret as gas data
                    data_start = 3 if response[1] in [0x03, 0x04] else 2
                    if len(response) >= data_start + 4:
                        print("  Potential gas readings:")
                        for i in range(data_start, min(len(response)-2, data_start+8), 2):
                            if i+1 < len(response):
                                value = int.from_bytes(response[i:i+2], 'big')
                                print(f"    Register {(i-data_start)//2}: {value} (0x{value:04X})")


import serial
import time
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
from SensorInterface import (
    BaseSensor, SensorReading, SensorStatus, AirQualityLevel, 
    SensorHealthMonitor, AirQualityAssessment, SensorFactory
)


class ZCE04BSensor(BaseSensor):
    """ZCE04B Multi-Gas Sensor Implementation"""
    
    # Class constants
    EXPECTED_RESPONSE_LENGTH = 13
    DEFAULT_BAUD = 9600
    MAX_RETRIES = 3
    RETRY_DELAY = 0.5
    READ_TIMEOUT = 3.0
    RESPONSE_WAIT = 0.3
    SENSOR_TYPE = "ZCE04B_MULTIGAS"

    def __init__(self, port: str, sensor_id: str = "ZCE04B_001",
                 baudrate: int = DEFAULT_BAUD):
        super().__init__(sensor_id, self.SENSOR_TYPE)
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.consecutive_failures = 0
        self.last_successful_read = None
        self.health_monitor = SensorHealthMonitor(sensor_id)
        
        # Gas concentration scaling factors (adjust based on sensor documentation)
        self.gas_scaling = {
            'CO': 0.1,      # Scale factor for CO readings
            'H2S': 0.01,    # Scale factor for H2S readings
            'CH4': 1.0,     # Scale factor for CH4 readings
            'O2': 0.1       # Scale factor for O2 readings
        }

    def connect(self) -> bool:
        """Connect to the ZCE04B sensor"""
        if self.status == SensorStatus.READY:
            return True

        try:
            self.status = SensorStatus.CONNECTING
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.READ_TIMEOUT,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )

            # Wait for connection to stabilize
            time.sleep(0.5)

            # Clear any existing data
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()

            self.status = SensorStatus.READY
            self.consecutive_failures = 0
            self.logger.info(f"Connected to {self.sensor_id} on {self.port}")
            return True

        except Exception as e:
            self.status = SensorStatus.ERROR
            self.logger.error(f"Connection failed: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from the sensor"""
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.status = SensorStatus.DISCONNECTED
        self.logger.info(f"Disconnected {self.sensor_id}")

    def _calculate_crc16_modbus(self, data: bytes) -> int:
        """Calculate CRC16 for Modbus RTU protocol"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def _create_modbus_frame(self, slave_id: int, function_code: int, 
                           start_reg: int, num_regs: int) -> bytearray:
        """Create a proper Modbus RTU frame"""
        frame = bytearray([
            slave_id,           # Slave address
            function_code,      # Function code
            (start_reg >> 8) & 0xFF,  # Start register high byte
            start_reg & 0xFF,   # Start register low byte
            (num_regs >> 8) & 0xFF,   # Number of registers high byte
            num_regs & 0xFF     # Number of registers low byte
        ])

        # Calculate CRC
        crc = self._calculate_crc16_modbus(frame)
        frame.append(crc & 0xFF)        # CRC low byte
        frame.append((crc >> 8) & 0xFF) # CRC high byte

        return frame

    def _send_request(self, frame: bytearray) -> Optional[bytes]:
        """Send a Modbus request and return response"""
        if not self.ser or not self.ser.is_open:
            return None

        try:
            # Clear input buffer
            self.ser.reset_input_buffer()
            
            # Send request
            self.ser.write(frame)
            self.ser.flush()
            
            # Wait for response
            time.sleep(self.RESPONSE_WAIT)
            
            # Read response
            if self.ser.in_waiting > 0:
                response = self.ser.read(self.ser.in_waiting)
                return response
            
            return None
            
        except Exception as e:
            self.logger.error(f"Communication error: {e}")
            return None

    def _validate_response(self, response: bytes, expected_slave_id: int) -> bool:
        """Validate Modbus response"""
        if not response or len(response) < 3:
            return False
            
        # Check if it's an error response
        if response[1] & 0x80:
            self.logger.error(f"Modbus error response: {response[2] if len(response) > 2 else 'Unknown'}")
            return False
            
        # Basic validation
        if response[0] != expected_slave_id and expected_slave_id != 0xFF:
            self.logger.warning(f"Unexpected slave ID: {response[0]}, expected: {expected_slave_id}")
            
        return True

    def read_data(self) -> Optional[SensorReading]:
        """Read gas sensor data from ZCE04B (implements BaseSensor interface)"""
        if self.status != SensorStatus.READY:
            if not self.connect():
                self.health_monitor.record_error()
                return None

        self.status = SensorStatus.READING

        # Define frame variations to try
        frame_variations = [
            # Standard Modbus read holding registers
            (0x01, 0x03, 0x0000, 0x0004, "Read 4 holding registers from 0x0000"),
            (0x01, 0x04, 0x0000, 0x0004, "Read 4 input registers from 0x0000"),
            # ZCE04B specific variations
            (0x01, 0x03, 0x0086, 0x0001, "Read holding register 0x86"),
            (0x01, 0x04, 0x0086, 0x0001, "Read input register 0x86"),
            # Try different slave addresses
            (0xFF, 0x03, 0x0000, 0x0004, "Broadcast read holding registers"),
        ]

        for slave_id, func_code, start_reg, num_regs, description in frame_variations:
            frame = self._create_modbus_frame(slave_id, func_code, start_reg, num_regs)
            
            for retry in range(self.MAX_RETRIES):
                response = self._send_request(frame)
                
                if response and self._validate_response(response, slave_id):
                    gas_data = self._parse_gas_data(response)
                    if gas_data:
                        self.consecutive_failures = 0
                        self.last_successful_read = datetime.now()
                        self.status = SensorStatus.READY
                        self.health_monitor.record_successful_read()
                        
                        # Assess air quality
                        quality_level = AirQualityAssessment.assess_overall_quality(gas_data)
                        
                        return SensorReading(
                            timestamp=datetime.now(),
                            sensor_id=self.sensor_id,
                            sensor_type=self.sensor_type,
                            data=gas_data,
                            status=SensorStatus.READY,
                            quality_level=quality_level,
                            raw_data=response
                        )
                
                time.sleep(self.RETRY_DELAY)
            
            self.logger.debug(f"Failed to get response with {description}")

        # If all variations fail
        self.consecutive_failures += 1
        self.health_monitor.record_error()
        
        if self.consecutive_failures >= self.MAX_RETRIES:
            self.status = SensorStatus.ERROR
        else:
            self.status = SensorStatus.READY
            
        return None

    def _parse_gas_data(self, response: bytes) -> Optional[Dict[str, float]]:
        """Parse gas sensor data from response"""
        try:
            # ZCE04B typically returns data in specific format
            # This is a generic parser - adjust based on actual sensor documentation
            
            if len(response) < 7:  # Minimum expected response length
                return None
                
            # Skip slave ID and function code
            data_start = 3 if response[1] in [0x03, 0x04] else 2
            
            if len(response) < data_start + 4:
                return None
                
            # Parse gas concentrations (adjust based on actual sensor format)
            # ZCE04B may return data in different formats, so we try multiple parsing methods
            
            try:
                # Method 1: 16-bit big-endian values
                if len(response) >= data_start + 8:
                    co_raw = int.from_bytes(response[data_start:data_start+2], 'big')
                    h2s_raw = int.from_bytes(response[data_start+2:data_start+4], 'big')
                    ch4_raw = int.from_bytes(response[data_start+4:data_start+6], 'big')
                    o2_raw = int.from_bytes(response[data_start+6:data_start+8], 'big')
                else:
                    # Method 2: Single byte values
                    co_raw = response[data_start] if len(response) > data_start else 0
                    h2s_raw = response[data_start+1] if len(response) > data_start+1 else 0
                    ch4_raw = response[data_start+2] if len(response) > data_start+2 else 0
                    o2_raw = response[data_start+3] if len(response) > data_start+3 else 0
                
                # Apply scaling factors
                gas_data = {
                    'CO': co_raw * self.gas_scaling['CO'],
                    'H2S': h2s_raw * self.gas_scaling['H2S'],
                    'CH4': ch4_raw * self.gas_scaling['CH4'],
                    'O2': o2_raw * self.gas_scaling['O2']
                }
                
                # Add additional info if available
                if len(response) > data_start + 8:
                    gas_data['temperature'] = response[data_start+8] if len(response) > data_start+8 else 0
                    gas_data['humidity'] = response[data_start+9] if len(response) > data_start+9 else 0
                
                # Validate readings (basic sanity check)
                if all(0 <= value <= 10000 for value in gas_data.values()):
                    return gas_data
                else:
                    self.logger.warning(f"Gas readings out of expected range: {gas_data}")
                    return None
                    
            except Exception as parse_error:
                self.logger.error(f"Error parsing gas concentrations: {parse_error}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error parsing gas data: {e}")
            return None

    def get_health_report(self) -> Dict:
        """Get sensor health report"""
        return self.health_monitor.get_health_report()

    def calibrate(self, calibration_data: Dict[str, float]) -> bool:
        """Update sensor calibration parameters"""
        try:
            # Update gas scaling factors
            for gas, factor in calibration_data.items():
                if gas in self.gas_scaling:
                    self.gas_scaling[gas] = factor
                    self.logger.info(f"Updated {gas} scaling factor to {factor}")
            return True
        except Exception as e:
            self.logger.error(f"Calibration failed: {e}")
            return False


class ZCE04BSensorTester:
    """Helper class for testing and debugging ZCE04B sensor communication"""
    
    def __init__(self, port: str, baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        
    def print_hex_bytes(self, data: bytes, label: str = "Data"):
        """Helper function to print bytes in hex format"""
        hex_str = ' '.join([f'{b:02X}' for b in data])
        print(f"{label}: [{hex_str}] (Length: {len(data)})")

    def test_sensor_communication(self) -> bool:
        """Test basic sensor communication"""
        sensor = ZCE04BSensor(self.port, baudrate=self.baudrate)
        
        try:
            if sensor.connect():
                print("✓ Sensor connected successfully")
                
                # Try to read data
                reading = sensor.read_data()
                if reading:
                    print("✓ Data read successfully")
                    print(f"Gas data: {reading.data}")
                    print(f"Quality level: {reading.quality_level}")
                    return True
                else:
                    print("✗ Failed to read data")
                    return False
            else:
                print("✗ Failed to connect to sensor")
                return False
                
        except Exception as e:
            print(f"✗ Test failed: {e}")
            return False
        finally:
            sensor.disconnect()

    def comprehensive_test(self) -> None:
        """Run comprehensive sensor test"""
        print("\n" + "="*60)
        print("🔬 COMPREHENSIVE ZCE04B SENSOR TEST")
        print("="*60)
        
        # Test basic communication
        if self.test_sensor_communication():
            print("🎉 Basic communication test PASSED")
        else:
            print("❌ Basic communication test FAILED")
            
        # Test with context manager
        print("\n🧪 Testing with context manager...")
        try:
            with ZCE04BSensor(self.port, baudrate=self.baudrate) as sensor:
                reading = sensor.read_data()
                if reading:
                    print("✓ Context manager test PASSED")
                    print(f"Reading: {reading.to_dict()}")
                else:
                    print("✗ Context manager test FAILED - no reading")
        except Exception as e:
            print(f"✗ Context manager test FAILED: {e}")


# Register the sensor type with the factory
SensorFactory.register_sensor_type('ZCE04B', ZCE04BSensor)


# Example usage
if __name__ == "__main__":
    # For normal operation
    sensor = ZCE04BSensor('/dev/ttyUSB0', sensor_id="GAS_SENSOR_01")
    
    if sensor.connect():
        reading = sensor.read_data()
        if reading:
            print(f"Gas data: {reading.data}")
            print(f"Air quality: {AirQualityAssessment.get_quality_description(reading.quality_level)}")
        sensor.disconnect()
    
    # For testing and debugging
    tester = ZCE04BSensorTester('/dev/ttyUSB0')
    tester.comprehensive_test()


