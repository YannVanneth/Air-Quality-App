import time
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Protocol, Callable
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('AirQualityMonitor')

# =============================================================================
# DATA MODELS (Fixed)
# =============================================================================


class SensorType(Enum):
    """Sensor type enumeration"""
    FORMALDEHYDE = "formaldehyde"
    CO2 = "co2"
    PARTICULATE = "particulate"
    MULTIGAS = "multigas"
    POLLUTION_LEVEL = "pollution_level"


class AirQualityLevel(Enum):
    """Air quality level enumeration"""
    EXCELLENT = "excellent"
    GOOD = "good"
    MODERATE = "moderate"
    POOR = "poor"
    HAZARDOUS = "hazardous"
    ERROR = "error"


@dataclass
class SensorReading:
    """Standardized sensor reading format"""
    sensor_id: str
    sensor_type: str
    timestamp: datetime
    values: Dict[str, float]
    quality: str = "GOOD"
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SensorReading':
        """Create from dictionary"""
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

    def is_valid(self) -> bool:
        """Check if reading is valid"""
        return self.error is None and bool(self.values) and self.quality != "ERROR"

    def get_primary_value(self) -> Optional[float]:
        """Get the primary measurement value"""
        if not self.values:
            return None
        # Return the first numeric value
        for value in self.values.values():
            if isinstance(value, (int, float)):
                return float(value)
        return None


@dataclass
class SensorConfig:
    """Configuration for a sensor"""
    sensor_id: str
    sensor_type: str
    connection_params: Dict[str, Any]
    calibration_params: Optional[Dict[str, float]] = None
    thresholds: Optional[Dict[str, float]] = None
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SensorConfig':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class AirQualitySnapshot:
    """Air quality snapshot with all sensor readings"""
    timestamp: datetime
    readings: List[SensorReading]
    overall_quality: str
    aqi_score: Optional[float] = None
    health_recommendations: Optional[List[str]] = None
    alerts: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'readings': [r.to_dict() for r in self.readings],
            'overall_quality': self.overall_quality,
            'aqi_score': self.aqi_score,
            'health_recommendations': self.health_recommendations or [],
            'alerts': self.alerts or []
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AirQualitySnapshot':
        data = data.copy()
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        data['readings'] = [SensorReading.from_dict(
            r) for r in data['readings']]
        return cls(**data)

    def get_readings_by_type(self, sensor_type: str) -> List[SensorReading]:
        return [r for r in self.readings if r.sensor_type == sensor_type]

    def get_readings_by_id(self, sensor_id: str) -> Optional[SensorReading]:
        for reading in self.readings:
            if reading.sensor_id == sensor_id:
                return reading
        return None

    def has_error(self) -> bool:
        return any(not r.is_valid() for r in self.readings)

    def get_valid_readings(self) -> List[SensorReading]:
        return [r for r in self.readings if r.is_valid()]


@dataclass
class SystemHealth:
    """System health status"""
    timestamp: datetime
    total_sensors: int
    healthy_sensors: int
    failed_sensors: int
    monitoring_active: bool
    uptime_seconds: float
    ml_model_ready: bool = False
    last_error: Optional[str] = None

    @property
    def health_percentage(self) -> float:
        """Calculate health percentage"""
        if self.total_sensors == 0:
            return 0.0
        return (self.healthy_sensors / self.total_sensors) * 100

    @property
    def is_healthy(self) -> bool:
        """Check if system is healthy"""
        return self.health_percentage >= 80 and self.monitoring_active

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['health_percentage'] = self.health_percentage
        data['is_healthy'] = self.is_healthy
        return data

# Quality assessment functions


class QualityAssessment:
    """Static methods for assessing air quality levels"""

    FORMALDEHYDE_THRESHOLDS = {
        AirQualityLevel.EXCELLENT: 0.08,
        AirQualityLevel.GOOD: 0.1,
        AirQualityLevel.MODERATE: 0.12,
        AirQualityLevel.POOR: 0.16
    }

    CO2_THRESHOLDS = {
        AirQualityLevel.EXCELLENT: 600,
        AirQualityLevel.GOOD: 1000,
        AirQualityLevel.MODERATE: 1500,
        AirQualityLevel.POOR: 2000
    }

    @staticmethod
    def assess_formaldehyde(mg_m3: float) -> AirQualityLevel:
        """Assess formaldehyde level"""
        thresholds = QualityAssessment.FORMALDEHYDE_THRESHOLDS
        if mg_m3 < thresholds[AirQualityLevel.EXCELLENT]:
            return AirQualityLevel.EXCELLENT
        elif mg_m3 < thresholds[AirQualityLevel.GOOD]:
            return AirQualityLevel.GOOD
        elif mg_m3 < thresholds[AirQualityLevel.MODERATE]:
            return AirQualityLevel.MODERATE
        elif mg_m3 < thresholds[AirQualityLevel.POOR]:
            return AirQualityLevel.POOR
        else:
            return AirQualityLevel.HAZARDOUS

    @staticmethod
    def assess_co2(ppm: float) -> AirQualityLevel:
        """Assess CO2 level"""
        thresholds = QualityAssessment.CO2_THRESHOLDS
        if ppm < thresholds[AirQualityLevel.EXCELLENT]:
            return AirQualityLevel.EXCELLENT
        elif ppm < thresholds[AirQualityLevel.GOOD]:
            return AirQualityLevel.GOOD
        elif ppm < thresholds[AirQualityLevel.MODERATE]:
            return AirQualityLevel.MODERATE
        elif ppm < thresholds[AirQualityLevel.POOR]:
            return AirQualityLevel.POOR
        else:
            return AirQualityLevel.HAZARDOUS

    @staticmethod
    def get_overall_quality(readings: List[SensorReading]) -> AirQualityLevel:
        """Determine overall air quality from multiple readings"""
        if not readings:
            return AirQualityLevel.ERROR

        # Quality level scoring (lower is better)
        quality_scores = {
            AirQualityLevel.EXCELLENT: 1,
            AirQualityLevel.GOOD: 2,
            AirQualityLevel.MODERATE: 3,
            AirQualityLevel.POOR: 4,
            AirQualityLevel.HAZARDOUS: 5,
            AirQualityLevel.ERROR: 6
        }

        scores = []
        for reading in readings:
            if reading.error:
                scores.append(quality_scores[AirQualityLevel.ERROR])
            else:
                # Convert string quality to enum and get score
                try:
                    quality_enum = AirQualityLevel(reading.quality.lower())
                    scores.append(quality_scores[quality_enum])
                except (ValueError, KeyError):
                    scores.append(quality_scores[AirQualityLevel.ERROR])

        if not scores:
            return AirQualityLevel.ERROR

        # Use worst quality as overall (highest score)
        worst_score = max(scores)

        # Convert back to quality level
        for level, score in quality_scores.items():
            if score == worst_score:
                return level

        return AirQualityLevel.ERROR
