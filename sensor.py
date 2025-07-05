
import serial
import time
import json
import logging
import threading
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum
from datetime import datetime
import sqlite3
from pathlib import Path
import statistics


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class SensorStatus(Enum):
    """Sensor status enumeration"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    WARMING_UP = "warming_up"
    READY = "ready"
    READING = "reading"
    ERROR = "error"
    FAULT = "fault"


class AirQualityLevel(Enum):
    EXCELLENT = 0
    GOOD = 1
    MODERATE = 2
    UNHEALTHY_SENSITIVE = 3
    UNHEALTHY = 4
    VERY_UNHEALTHY = 5
    HAZARDOUS = 6


@dataclass
class SensorReading:
    timestamp: datetime
    sensor_id: str
    sensor_type: str
    data: Dict[str, float]
    status: SensorStatus
    quality_level: AirQualityLevel
    raw_data: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'sensor_id': self.sensor_id,
            'sensor_type': self.sensor_type,
            'data': self.data,
            'status': self.status.value,
            'quality_level': self.quality_level.value,
            'raw_data': self.raw_data.hex() if self.raw_data else None
        }


class ZCE04BSensor:
    def __init__(self, port: str = '/dev/ttyS0', baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.logger = logging.getLogger(f"{__name__}.ZCE04B")
        self.status = SensorReading.DISCONNECTED
        self.last_reading = None

    def connect(self) -> bool:
        try:
            self.status = SensorStatus.CONNECTING
            self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
            self.logger.info(f"Connected to ZCE04B on {
                             self.port} at {self.baudrate} baud")
            self.status = SensorStatus.READY
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to ZCE04B: {e}")
            self.status = SensorStatus.ERROR
            return False

    def calculate_crc16_modbus(self, data: bytes) -> int:
        """Calculate CRC16 for Modbus RTU"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

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


class ZH07Sensor:
    def __init__(self, port: str = '/dev/ttyS0', baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.logger = logging.getLogger(f'{__name__}.ZH07')
        self.status = SensorStatus.DISCONNECTED
        self.last_reading = None

    def connect(self) -> bool:
        try:
            self.status = SensorStatus.CONNECTING
            self.ser = serial.Serial(self.port, self.baudrate, timeout=2)
            self.ser.reset_input_buffer()
            self.logger.info(f"Connected to ZH07 on {
                             self.port} at {self.baudrate} baud")
            self.status = SensorStatus.READY
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to ZH07: {e}")
            self.status = SensorStatus.ERROR
            return False

    def read_data(self) -> Optional[SensorReading]:
        """Read PM2.5 and PM10 data"""
        if self.status != SensorStatus.READY:
            return None

        try:
            self.status = SensorStatus.READING

            # Look for BM header
            buffer = bytearray()
            start_time = time.time()

            while time.time() - start_time < 3:  # 3 second timeout
                if self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting)
                    buffer.extend(data)

                    # Look for BM header (0x42 0x4D)
                    for i in range(len(buffer) - 8):
                        if buffer[i] == 0x42 and buffer[i+1] == 0x4D:
                            if i + 8 < len(buffer):
                                packet = buffer[i:i+9]

                                # Verify checksum
                                calculated_checksum = sum(packet[0:8]) % 256
                                if calculated_checksum == packet[8]:
                                    # Extract PM values
                                    pm25 = (packet[2] << 8) | packet[3]
                                    pm10 = (packet[4] << 8) | packet[5]

                                    data = {
                                        'pm25_ugm3': pm25,
                                        'pm10_ugm3': pm10
                                    }

                                    quality_level = self._determine_quality_level(
                                        data)

                                    reading = SensorReading(
                                        timestamp=datetime.now(),
                                        sensor_id='ZH07_001',
                                        sensor_type='particulate_matter',
                                        data=data,
                                        status=SensorStatus.READY,
                                        quality_level=quality_level,
                                        raw_data=bytes(packet)
                                    )

                                    self.last_reading = reading
                                    self.status = SensorStatus.READY
                                    return reading

                time.sleep(0.1)

        except Exception as e:
            self.logger.error(f"Error reading ZH07 data: {e}")
            self.status = SensorStatus.ERROR

        self.status = SensorStatus.READY
        return None

    def _determine_quality_level(self, data: Dict[str, float]) -> AirQualityLevel:
        """Determine air quality level based on PM concentrations"""
        pm25 = data.get('pm25_ugm3', 0)
        pm10 = data.get('pm10_ugm3', 0)

        if pm25 > 250 or pm10 > 430:
            return AirQualityLevel.HAZARDOUS
        elif pm25 > 150 or pm10 > 355:
            return AirQualityLevel.VERY_UNHEALTHY
        elif pm25 > 55 or pm10 > 155:
            return AirQualityLevel.UNHEALTHY
        elif pm25 > 35 or pm10 > 55:
            return AirQualityLevel.UNHEALTHY_SENSITIVE
        elif pm25 > 12 or pm10 > 55:
            return AirQualityLevel.MODERATE
        else:
            return AirQualityLevel.GOOD

    def disconnect(self):
        """Disconnect from sensor"""
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.status = SensorStatus.DISCONNECTED


class ZP07Sensor:

    def __init__(self, warm_up_time: int = 180):
        self.warm_up_time = warm_up_time
        self.logger = logging.getLogger(f'{__name__}.ZP07')
        self.status = SensorStatus.DISCONNECTED
        self.last_reading = None
        self.start_time = None
        self.is_warmed_up = False

    def connect(self) -> bool:
        """Initialize sensor (no serial connection needed for PWM)"""
        try:
            self.status = SensorStatus.CONNECTING
            self.start_time = time.time()
            self.logger.info("Initializing ZP07-MP503 sensor")

            # Start warm-up
            self.status = SensorStatus.WARMING_UP
            threading.Thread(target=self._warm_up_process, daemon=True).start()

            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize ZP07: {e}")
            self.status = SensorStatus.ERROR
            return False

    def _warm_up_process(self):
        """Warm-up process"""
        self.logger.info(f"Starting warm-up process ({self.warm_up_time}s)")
        time.sleep(self.warm_up_time)
        self.is_warmed_up = True
        self.status = SensorStatus.READY
        self.logger.info("Warm-up completed - sensor ready")

    def read_data(self) -> Optional[SensorReading]:
        """Read air quality data (simulated PWM reading)"""
        if not self.is_warmed_up:
            return None

        try:
            self.status = SensorStatus.READING

            # Simulate PWM reading and pollution level detection
            import random
            pollution_level = random.randint(0, 10)

            # Simulate detected gas concentrations
            base_concentration = pollution_level * 10
            data = {
                'pollution_level': pollution_level,
                'formaldehyde_ppb': base_concentration + random.uniform(-5, 5),
                'benzene_ppb': base_concentration * 0.8 + random.uniform(-3, 3),
                'co_ppm': base_concentration * 0.1 + random.uniform(-1, 1),
                'alcohol_ppm': base_concentration * 0.05 + random.uniform(-2, 2),
                'ammonia_ppm': base_concentration * 0.02 + random.uniform(-1, 1)
            }

            # Ensure non-negative values
            for key in data:
                if key != 'pollution_level':
                    data[key] = max(0, data[key])

            quality_level = self._determine_quality_level(data)

            reading = SensorReading(
                timestamp=datetime.now(),
                sensor_id='ZP07_001',
                sensor_type='volatile_organic_compounds',
                data=data,
                status=SensorStatus.READY,
                quality_level=quality_level
            )

            self.last_reading = reading
            self.status = SensorStatus.READY
            return reading

        except Exception as e:
            self.logger.error(f"Error reading ZP07 data: {e}")
            self.status = SensorStatus.ERROR

        self.status = SensorStatus.READY
        return None

    def _determine_quality_level(self, data: Dict[str, float]) -> AirQualityLevel:
        """Determine air quality level based on pollution level"""
        pollution_level = data.get('pollution_level', 0)

        if pollution_level >= 9:
            return AirQualityLevel.HAZARDOUS
        elif pollution_level >= 7:
            return AirQualityLevel.VERY_UNHEALTHY
        elif pollution_level >= 5:
            return AirQualityLevel.UNHEALTHY
        elif pollution_level >= 3:
            return AirQualityLevel.UNHEALTHY_SENSITIVE
        elif pollution_level >= 1:
            return AirQualityLevel.MODERATE
        else:
            return AirQualityLevel.GOOD

    def disconnect(self):
        """Disconnect sensor"""
        self.status = SensorStatus.DISCONNECTED


def main():
    logging.info("Starting air quality monitoring system on Raspberry Pi...")

    zce04b = ZCE04BSensor(port='/dev/ttyS0')
    zh07 = ZH07Sensor(port='/dev/ttyS0')
    zp07 = ZP07Sensor(warm_up_time=10)

    zce04b.connect()
    time.sleep(1)
    zh07.connect()
    zp07.connect()

    try:
        while True:
            readings = []

            zce04b_reading = zce04b.read_data()
            if zce04b_reading:
                readings.append(zce04b_reading)

            zh07_reading = zh07.read_data()
            if zh07_reading:
                readings.append(zh07_reading)

            zp07_reading = zp07.read_data()
            if zp07_reading:
                readings.append(zp07_reading)

            for reading in readings:
                print(json.dumps(reading.to_dict(), indent=2))

            time.sleep(5)

    except KeyboardInterrupt:
        logging.info("Shutting down sensors...")

    finally:
        zce04b.disconnect()
        zh07.disconnect()
        zp07.disconnect()
        logging.info("System shut down.")


if __name__ == "__main__":
    main()
