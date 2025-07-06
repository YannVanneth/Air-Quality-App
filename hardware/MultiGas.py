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

from SensorInterface import (
    SensorReading, SensorStatus, AirQualityLevel
)


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
