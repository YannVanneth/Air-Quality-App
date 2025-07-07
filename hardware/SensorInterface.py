from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from enum import Enum
from datetime import datetime
import logging
from dataclasses import dataclass




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
    """Air quality level enumeration"""
    EXCELLENT = 0
    GOOD = 1
    MODERATE = 2
    UNHEALTHY_SENSITIVE = 3
    UNHEALTHY = 4
    VERY_UNHEALTHY = 5
    HAZARDOUS = 6


@dataclass
class SensorReading:
    """Data structure for sensor readings"""
    timestamp: datetime
    sensor_id: str
    sensor_type: str
    data: Dict[str, float]
    status: SensorStatus
    quality_level: AirQualityLevel
    raw_data: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert sensor reading to dictionary format"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'sensor_id': self.sensor_id,
            'sensor_type': self.sensor_type,
            'data': self.data,
            'status': self.status.value,
            'quality_level': self.quality_level.value,
            'raw_data': self.raw_data.hex() if self.raw_data else None
        }


class BaseSensor(ABC):
    """Abstract base class for all sensor implementations"""

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the sensor. Returns True if successful."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the sensor."""
        pass

    @abstractmethod
    def read_data(self) -> Optional[SensorReading]:
        """Read data from the sensor. Returns SensorReading or None if failed."""
        pass

    def __enter__(self):
        """Context manager entry - connect to sensor"""
        if self.connect():
            return self
        else:
            raise RuntimeError("Failed to connect to sensor")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - disconnect from sensor"""
        self.disconnect()
        return False

