import serial
import time
import logging
from typing import Dict, Optional
from datetime import datetime
<<<<<<< HEAD
from SensorInterface import  SensorReading, SensorStatus, AirQualityLevel


class ZCE04BSensor:
    def __init__(self, port: str = '/dev/ttyS0', baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.logger = logging.getLogger(f"{__name__}.ZCE04B")
        self.status = SensorStatus.DISCONNECTED
        self.last_reading = None

    def connect(self) -> bool:
        try:
            self.status = SensorStatus.CONNECTING
            self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
            self.logger.info(f"Connected to ZCE04B on {self.port} at {self.baudrate} baud")
            self.status = SensorStatus.READY
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to ZCE04B: {e}")
            self.status = SensorStatus.ERROR
            return False

    def calculate_crc16_modbus(self, data: bytes) -> int:
        """Calculate CRC16 for Modbus RTU"""
=======
from SensorInterface import BaseSensor, SensorReading, SensorStatus, AirQualityLevel


class ZCE04BSensor(BaseSensor):
    EXPECTED_RESPONSE_LENGTH = 13
    DEFAULT_BAUD = 9600

    def __init__(self, port: str, sensor_id: str = "ZCE04B_001",
                 baudrate: int = DEFAULT_BAUD):
        self.port = port
        self.baudrate = baudrate
        self.sensor_id = sensor_id
        self.ser = None
        self.logger = logging.getLogger(f"{__name__}.ZCE04B")
        self.status = SensorStatus.DISCONNECTED

    def connect(self) -> bool:
        if self.status == SensorStatus.READY:
            return True
        try:
            self.status = SensorStatus.CONNECTING
            self.ser = serial.Serial(
                self.port,
                self.baudrate,
                timeout=2
            )
            self.status = SensorStatus.READY
            self.logger.info(f"Connected to {self.sensor_id} on {self.port}")
            return True
        except Exception as e:
            self.status = SensorStatus.ERROR
            self.logger.error(f"Connection failed: {e}")
            return False

    def disconnect(self) -> None:
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.status = SensorStatus.DISCONNECTED
        self.logger.info(f"Disconnected {self.sensor_id}")

    def _calculate_crc16_modbus(self, data: bytes) -> int:
        """Calculate CRC-16 Modbus checksum for given data."""
>>>>>>> bb2ccc373fbcc4c5633ff95ef34553c205043db8
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

<<<<<<< HEAD
    def create_modbus_frame(self, slave_id: int, function_code: int,
                            start_reg: int, num_regs: int) -> bytes:
        """Create Modbus RTU frame"""
        frame = bytearray([
            slave_id,
            function_code,
            (start_reg >> 8) & 0xFF,
            start_reg & 0xFF,
            (num_regs >> 8) & 0xFF,
            num_regs & 0xFF
        ])

        crc = self.calculate_crc16_modbus(frame)
        frame.append(crc & 0xFF)
        frame.append((crc >> 8) & 0xFF)

        return bytes(frame)

    def read_data(self) -> Optional[SensorReading]:
        """Read gas concentration data"""
        if self.status != SensorStatus.READY:
            return None

        try:
            self.status = SensorStatus.READING

            frame = self.create_modbus_frame(0x01, 0x03, 0x0000, 0x0004)

            if self.ser.in_waiting > 0:
                self.ser.read(self.ser.in_waiting)  # Clear buffer

            self.ser.write(frame)
            self.ser.flush()
            time.sleep(0.1)

            if self.ser.in_waiting > 0:
                response = self.ser.read(self.ser.in_waiting)

                # Parse response (simplified - actual parsing depends on sensor response format)
                if len(response) >= 9:
                    # Extract gas concentrations (example values)
                    co_ppm = (response[3] << 8) | response[4] if len(
                        response) > 4 else 0
                    h2s_ppm = (response[5] << 8) | response[6] if len(
                        response) > 6 else 0
                    ch4_ppm = (response[7] << 8) | response[8] if len(
                        response) > 8 else 0
                    o2_percent = response[9] if len(response) > 9 else 21

                    data = {
                        'co_ppm': co_ppm / 100.0,  # Convert to proper units
                        'h2s_ppm': h2s_ppm / 100.0,
                        'ch4_ppm': ch4_ppm / 100.0,
                        'o2_percent': o2_percent / 10.0
                    }

                    # Determine air quality level based on gas concentrations
                    quality_level = self._determine_quality_level(data)

                    reading = SensorReading(
                        timestamp=datetime.now(),
                        sensor_id='ZCE04B_001',
                        sensor_type='multi_gas',
                        data=data,
                        status=SensorStatus.READY,
                        quality_level=quality_level,
                        raw_data=response
                    )

                    self.last_reading = reading
                    self.status = SensorStatus.READY
                    return reading

        except Exception as e:
            self.logger.error(f"Error reading ZCE04B data: {e}")
            self.status = SensorStatus.ERROR

        self.status = SensorStatus.READY
        return None

    def _determine_quality_level(self, data: Dict[str, float]) -> AirQualityLevel:
        """Determine air quality level based on gas concentrations"""
        co_ppm = data.get('co_ppm', 0)
        h2s_ppm = data.get('h2s_ppm', 0)

        if co_ppm > 35 or h2s_ppm > 10:
            return AirQualityLevel.HAZARDOUS
        elif co_ppm > 15 or h2s_ppm > 5:
            return AirQualityLevel.VERY_UNHEALTHY
        elif co_ppm > 9 or h2s_ppm > 2:
            return AirQualityLevel.UNHEALTHY
        elif co_ppm > 4 or h2s_ppm > 1:
            return AirQualityLevel.UNHEALTHY_SENSITIVE
        elif co_ppm > 2 or h2s_ppm > 0.5:
            return AirQualityLevel.MODERATE
        else:
            return AirQualityLevel.GOOD

    def disconnect(self):
        """Disconnect from sensor"""
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.status = SensorStatus.DISCONNECTED

=======
    def _create_modbus_frame(self) -> bytes:
        """Create Modbus RTU frame for reading sensor data."""
        frame = bytearray([0x01, 0x03, 0x00, 0x00, 0x00, 0x04])
        crc = self._calculate_crc16_modbus(frame)
        frame.append(crc & 0xFF)
        frame.append((crc >> 8) & 0xFF)
        return bytes(frame)

    def _parse_response(self, response: bytes) -> Dict[str, float]:
        """Parse Modbus response containing gas sensor data."""
        if len(response) != self.EXPECTED_RESPONSE_LENGTH:
            raise ValueError(f"Invalid response length: {len(response)} bytes")

        # Verify CRC
        crc = self._calculate_crc16_modbus(response[:-2])
        if crc != int.from_bytes(response[-2:], 'little'):
            raise ValueError("CRC mismatch")

        return {
            'co_ppm': int.from_bytes(response[3:5], 'big') / 100.0,
            'h2s_ppm': int.from_bytes(response[5:7], 'big') / 100.0,
            'ch4_ppm': int.from_bytes(response[7:9], 'big') / 100.0,
            'o2_percent': int.from_bytes(response[9:11], 'big') / 10.0
        }

    def _determine_quality_level(self, data: Dict[str, float]) -> AirQualityLevel:
        """Determine air quality level based on gas concentrations."""
        co = data['co_ppm']
        h2s = data['h2s_ppm']

        if co > 35 or h2s > 10:
            return AirQualityLevel.HAZARDOUS
        elif co > 15 or h2s > 5:
            return AirQualityLevel.VERY_UNHEALTHY
        elif co > 9 or h2s > 2:
            return AirQualityLevel.UNHEALTHY
        elif co > 4 or h2s > 1:
            return AirQualityLevel.UNHEALTHY_SENSITIVE
        elif co > 2 or h2s > 0.5:
            return AirQualityLevel.MODERATE
        return AirQualityLevel.GOOD

    def read_data(self) -> Optional[SensorReading]:
        """Read gas sensor data via Modbus RTU."""
        if self.status != SensorStatus.READY:
            self.logger.warning("Sensor not ready for reading")
            return None

        try:
            self.status = SensorStatus.READING
            frame = self._create_modbus_frame()

            # Clear buffers
            self.ser.reset_input_buffer()
            self.ser.write(frame)
            time.sleep(0.2)

            response = self.ser.read(self.EXPECTED_RESPONSE_LENGTH)
            if not response:
                return None

            gas_data = self._parse_response(response)

            return SensorReading(
                timestamp=datetime.now(),
                sensor_id=self.sensor_id,
                sensor_type='multi_gas',
                data=gas_data,
                status=SensorStatus.READY,
                quality_level=self._determine_quality_level(gas_data),
                raw_data=response
            )

        except Exception as e:
            self.status = SensorStatus.ERROR
            self.logger.error(f"Read failed: {e}")
            return None
        finally:
            if self.status != SensorStatus.ERROR:
                self.status = SensorStatus.READY


# if __name__ == "__main__":
#    # Configure logging
#    logging.basicConfig(level=logging.INFO)
#
#    # Example usage (commented out since we don't have actual hardware)
#    """
#    sensor = ZCE04BSensor("/dev/ttyUSB0", "ZCE04B_Test")
#
#    if sensor.connect():
#        reading = sensor.read_data()
#        if reading:
#            print(f"Sensor Reading: {reading.data}")
#            print(f"Air Quality: {reading.quality_level}")
#        sensor.disconnect()
#    """
#
#    # Test CRC calculation
#    sensor = ZCE04BSensor("dummy_port")
#    test_frame = bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x04])
#    crc = sensor._calculate_crc16_modbus(test_frame)
#    print(f"Test CRC calculation: 0x{crc:04X}")
#
#    # Test frame creation
#    complete_frame = sensor._create_modbus_frame()
#    print(f"Complete Modbus frame: {[hex(b) for b in complete_frame]}")
#
#    # Test response parsing with simulated data
#    simulated_response = bytearray([0x01, 0x03, 0x08])  # Device ID, Function code, byte count
#    simulated_response.extend([0x00, 0x64])  # CO: 100 (1.00 ppm)
#    simulated_response.extend([0x00, 0x32])  # H2S: 50 (0.50 ppm)
#    simulated_response.extend([0x03, 0xE8])  # CH4: 1000 (10.00 ppm)
#    simulated_response.extend([0x00, 0xD2])  # O2: 210 (21.0%)
#
#    # Add CRC
#    crc = sensor._calculate_crc16_modbus(simulated_response)
#    simulated_response.append(crc & 0xFF)
#    simulated_response.append((crc >> 8) & 0xFF)
#
#    try:
#        parsed_data = sensor._parse_response(bytes(simulated_response))
#        print(f"Parsed gas data: {parsed_data}")
#        quality = sensor._determine_quality_level(parsed_data)
#        print(f"Air quality level: {quality}")
#    except ValueError as e:
#        print(f"Error parsing response: {e}")
>>>>>>> bb2ccc373fbcc4c5633ff95ef34553c205043db8

