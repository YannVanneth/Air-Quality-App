from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Optional, Any
import datetime
import logging
from dataclasses import dataclass


class SensorStatus(Enum):
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
    timestamp: datetime.datetime
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


class BaseSensor(ABC):
    """Abstract base class for all sensors"""
    
    def __init__(self, sensor_id: str, sensor_type: str):
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.logger = logging.getLogger(f"{__name__}.{sensor_type}")
        self.status = SensorStatus.DISCONNECTED
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the sensor"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the sensor"""
        pass
    
    @abstractmethod
    def read_data(self) -> Optional[SensorReading]:
        """Read data from the sensor"""
        pass
    
    def get_status(self) -> SensorStatus:
        """Get current sensor status"""
        return self.status
    
    def get_sensor_id(self) -> str:
        """Get sensor ID"""
        return self.sensor_id
    
    def get_sensor_type(self) -> str:
        """Get sensor type"""
        return self.sensor_type
    
    def is_connected(self) -> bool:
        """Check if sensor is connected and ready"""
        return self.status in [SensorStatus.READY, SensorStatus.READING]
    
    def __enter__(self):
        """Context manager entry"""
        if self.connect():
            return self
        else:
            raise RuntimeError(f"Failed to connect to sensor {self.sensor_id}")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
        return False  # Don't suppress exceptions


class SensorCalibration:
    """Helper class for sensor calibration data"""
    
    def __init__(self, calibration_data: Dict[str, float]):
        self.calibration_data = calibration_data
        self.calibration_timestamp = datetime.datetime.now()
    
    def apply_calibration(self, raw_value: float, parameter: str) -> float:
        """Apply calibration to raw sensor value"""
        if parameter in self.calibration_data:
            # Simple linear calibration: calibrated = raw * factor + offset
            factor = self.calibration_data.get(f"{parameter}_factor", 1.0)
            offset = self.calibration_data.get(f"{parameter}_offset", 0.0)
            return raw_value * factor + offset
        return raw_value


class SensorHealthMonitor:
    """Monitor sensor health and performance"""
    
    def __init__(self, sensor_id: str):
        self.sensor_id = sensor_id
        self.read_count = 0
        self.error_count = 0
        self.last_reading_time = None
        self.start_time = datetime.datetime.now()
    
    def record_successful_read(self):
        """Record a successful sensor read"""
        self.read_count += 1
        self.last_reading_time = datetime.datetime.now()
    
    def record_error(self):
        """Record a sensor error"""
        self.error_count += 1
    
    def get_success_rate(self) -> float:
        """Calculate success rate as percentage"""
        total_attempts = self.read_count + self.error_count
        if total_attempts == 0:
            return 0.0
        return (self.read_count / total_attempts) * 100.0
    
    def get_uptime(self) -> datetime.timedelta:
        """Get sensor uptime"""
        return datetime.datetime.now() - self.start_time
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        return {
            'sensor_id': self.sensor_id,
            'read_count': self.read_count,
            'error_count': self.error_count,
            'success_rate': self.get_success_rate(),
            'uptime': str(self.get_uptime()),
            'last_reading': self.last_reading_time.isoformat() if self.last_reading_time else None
        }


class AirQualityAssessment:
    """Utility class for air quality assessment"""
    
    # Standard thresholds for common pollutants (adjust based on your requirements)
    THRESHOLDS = {
        'CO': {  # Carbon Monoxide (ppm)
            AirQualityLevel.EXCELLENT: 0,
            AirQualityLevel.GOOD: 4.4,
            AirQualityLevel.MODERATE: 9.4,
            AirQualityLevel.UNHEALTHY_SENSITIVE: 12.4,
            AirQualityLevel.UNHEALTHY: 15.4,
            AirQualityLevel.VERY_UNHEALTHY: 30.4,
            AirQualityLevel.HAZARDOUS: 40.4
        },
        'H2S': {  # Hydrogen Sulfide (ppm)
            AirQualityLevel.EXCELLENT: 0,
            AirQualityLevel.GOOD: 0.01,
            AirQualityLevel.MODERATE: 0.02,
            AirQualityLevel.UNHEALTHY_SENSITIVE: 0.05,
            AirQualityLevel.UNHEALTHY: 0.1,
            AirQualityLevel.VERY_UNHEALTHY: 0.2,
            AirQualityLevel.HAZARDOUS: 0.5
        },
        'PM25': {  # PM2.5 (μg/m³)
            AirQualityLevel.EXCELLENT: 0,
            AirQualityLevel.GOOD: 12,
            AirQualityLevel.MODERATE: 35.4,
            AirQualityLevel.UNHEALTHY_SENSITIVE: 55.4,
            AirQualityLevel.UNHEALTHY: 150.4,
            AirQualityLevel.VERY_UNHEALTHY: 250.4,
            AirQualityLevel.HAZARDOUS: 500.4
        },
        'PM10': {  # PM10 (μg/m³)
            AirQualityLevel.EXCELLENT: 0,
            AirQualityLevel.GOOD: 54,
            AirQualityLevel.MODERATE: 154,
            AirQualityLevel.UNHEALTHY_SENSITIVE: 254,
            AirQualityLevel.UNHEALTHY: 354,
            AirQualityLevel.VERY_UNHEALTHY: 424,
            AirQualityLevel.HAZARDOUS: 604
        }
    }
    
    @classmethod
    def assess_pollutant(cls, value: float, pollutant: str) -> AirQualityLevel:
        """Assess air quality level for a specific pollutant"""
        if pollutant not in cls.THRESHOLDS:
            return AirQualityLevel.MODERATE  # Default for unknown pollutants
        
        thresholds = cls.THRESHOLDS[pollutant]
        
        for level in reversed(list(AirQualityLevel)):
            if value >= thresholds.get(level, float('inf')):
                return level
        
        return AirQualityLevel.EXCELLENT
    
    @classmethod
    def assess_overall_quality(cls, sensor_data: Dict[str, float]) -> AirQualityLevel:
        """Assess overall air quality based on multiple pollutants"""
        worst_level = AirQualityLevel.EXCELLENT
        
        for pollutant, value in sensor_data.items():
            level = cls.assess_pollutant(value, pollutant)
            if level.value > worst_level.value:
                worst_level = level
        
        return worst_level
    
    @classmethod
    def get_quality_description(cls, level: AirQualityLevel) -> str:
        """Get human-readable description of air quality level"""
        descriptions = {
            AirQualityLevel.EXCELLENT: "Air quality is excellent",
            AirQualityLevel.GOOD: "Air quality is good",
            AirQualityLevel.MODERATE: "Air quality is moderate",
            AirQualityLevel.UNHEALTHY_SENSITIVE: "Unhealthy for sensitive groups",
            AirQualityLevel.UNHEALTHY: "Unhealthy air quality",
            AirQualityLevel.VERY_UNHEALTHY: "Very unhealthy air quality",
            AirQualityLevel.HAZARDOUS: "Hazardous air quality"
        }
        return descriptions.get(level, "Unknown air quality level")


class SensorFactory:
    """Factory class for creating sensor instances"""
    
    _sensor_types = {}
    
    @classmethod
    def register_sensor_type(cls, sensor_type: str, sensor_class):
        """Register a new sensor type"""
        cls._sensor_types[sensor_type] = sensor_class
    
    @classmethod
    def create_sensor(cls, sensor_type: str, **kwargs) -> BaseSensor:
        """Create a sensor instance"""
        if sensor_type not in cls._sensor_types:
            raise ValueError(f"Unknown sensor type: {sensor_type}")
        
        sensor_class = cls._sensor_types[sensor_type]
        return sensor_class(**kwargs)
    
    @classmethod
    def get_available_types(cls) -> list:
        """Get list of available sensor types"""
        return list(cls._sensor_types.keys())

