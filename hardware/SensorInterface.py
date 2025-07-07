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
