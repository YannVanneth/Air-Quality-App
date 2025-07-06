import serial
import time
from typing import Optional, Dict, Union, List
import logging
from SensorInterface import SensorStatus


class ZH07:

    HEADER = b'BM'
    PACKET_SIZE = 9
    DEFAULT_TIMEOUT = 1.0
    DEFAULT_BAUD = 9600
    VALID_PM_RANGE = (0, 1000)

    def __init__(self, port: int, sensor_id: str = "ZH07_001",
                 timeout: float = DEFAULT_TIMEOUT, baud_rate: int = DEFAULT_BAUD):

        self.port = port
        self.timeout = timeout
        self.baud_rate = baud_rate
        self.sensor_id = sensor_id
        self.serial_conn = None
        self.logger = logging.getLogger(f"{__name__}.ZH07")
        self.status = SensorStatus.DISCONNECTED
        self.warm_up_done = False
        self.sensor_id = sensor_id

    def connect(self) -> bool:
        if self.status == SensorStatus.READY
        return True

        try:
            self.status = SensorStatus.CONNECTING
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )

            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()

            self.status = SensorStatus.WARMING_UP
            self.logger('warming up sensor 30 seconds')
            time.sleep(30)

            self.warm_up_done = True
            self.status = SensorStatus.READY
            self.logger.info(f"Connected to {self.sensor_id} on {self.port}")
            return True

    def disconnect(self) -> None:
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        self.status = SensorStatus.DISCONNECTED
        self.logger.info(f"Disconnected {self.sensor_id}")

    def _calculate_checksum(self, packet: bytes) -> int:
        return sum(packet[0:8]) % 256

    def _extract_valid_packet(self, data: bytes) -> Optional[bytes]:
        for i in range(len(data) - self.PACKET_SIZE + 1):
            if data[i:i+2] == self.HEADER:
                packet = data[i:i+self.PACKET_SIZE]
                if len(packet) == self.PACKET_SIZE:
                    if self._calculate_checksum(packet) == packet[8]:
                        return packet
            return None

    def _determine_quality_level(self, pm25: float) -> AirQualityLevel:
        if pm25 <= 12:
            return AirQualityLevel.EXCELLENT
        elif pm25 <= 35:
            return AirQualityLevel.GOOD
        elif pm25 <= 55:
            return AirQualityLevel.MODERATE
        elif pm25 <= 150:
            return AirQualityLevel.UNHEALTHY
        elif pm25 <= 250:
            return AirQualityLevel.VERY_UNHEALTHY
        return AirQualityLevel.HAZARDOUS

    def read_data(self) -> Optional[SensorReading]:
        if self.status != SensorStatus.READY:
            self.logger.warning("Sensor not ready for reading")
            return None

        try:
            self.status = SensorStatus.READING
            time.sleep(1.1)

            if self.serial_conn.in_waiting == 0:
                return None

            data = self.serial_conn.read(self.serial_conn.in_waiting)
            packet = self._extract_valid_packet(data)

            if not packet:
                self.logger.debug("No valid packet found")
                return None

            pm25 = (packet[2] << 8) | packet[3]
            pm10 = (packet[4] << 8) | packet[5]

            if not (self.VALID_PM_RANGE[0] <= pm25 <= self.VALID_PM_RANGE[1] and
                    self.VALID_PM_RANGE[0] <= pm10 <= self.VALID_PM_RANGE[1] and
                    pm10 >= pm25):
                raise ValueError(f"Invalid PM values: PM2.5={
                                 pm25}, PM10={pm10}")

            sensor_data = {
                'pm2.5': pm25,
                'pm10': pm10
            }

            return SensorReading(
                timestamp=datetime.now(),
                sensor_id=self.sensor_id,
                sensor_type='particulate_matter',
                data=sensor_data,
                status=SensorStatus.READY,
                quality_level=self._determine_quality_level(pm25),
                raw_data=bytes(packet)
            )

        except Exception as e:
            self.status = SensorStatus.ERROR
            self.logger.error(f"Read failed: {e}")
            return None
        finally:
            if self.status != SensorStatus.ERROR:
                self.status = SensorStatus.READY
