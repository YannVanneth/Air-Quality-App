import serial
import time
import logging
from typing import Dict, Optional
from datetime import datetime
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
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def _create_modbus_frame(self) -> bytes:
        frame = bytearray([0x01, 0x03, 0x00, 0x00, 0x00, 0x04])
        crc = self._calculate_crc16_modbus(frame)
        frame.append(crc & 0xFF)
        frame.append((crc >> 8) & 0xFF)
        return bytes(frame)

    def _parse_response(self, response: bytes) -> Dict[str, float]:
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
