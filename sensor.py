
from datetime import datetime
import random
from logging import info, error
from datetime import timezone
from typing import Optional, Callable, Dict, Any, Tuple
from data_models import logger
from data_models import (
    SensorConfig,
    SensorReading,
    AirQualityLevel,
    QualityAssessment
)
from interfaces import CommunicationInterface


class BaseSensor:
    """Base sensor class with common functionality"""

    def __init__(self, config: SensorConfig):
        self.config = config
        self.error_count = 0
        self.last_reading = None
        self.communication = None

    def get_config(self) -> SensorConfig:
        """Get sensor configuration"""
        return self.config

    def get_sensor_info(self) -> Dict[str, str]:
        """Get sensor metadata and status"""
        return {
            'sensor_id': self.config.sensor_id,
            'sensor_type': self.config.sensor_type,
            'status': 'healthy' if self.is_healthy() else 'error',
            'error_count': str(self.error_count)
        }

    def is_healthy(self) -> bool:
        """Check if sensor is functioning properly"""
        return self.error_count < 5

    def _create_error_reading(self, error_msg: str) -> SensorReading:
        """Create an error reading"""
        self.error_count += 1
        return SensorReading(
            sensor_id=self.config.sensor_id,
            sensor_type=self.config.sensor_type,
            timestamp=datetime.now(timezone.utc),
            values={},
            quality=AirQualityLevel.ERROR.value,
            error=error_msg,
            metadata={'error_count': self.error_count}
        )


class FormaldehydeSensor(BaseSensor):
    """Formaldehyde sensor implementation (ZE08-CH2O)"""

    def __init__(self, config: SensorConfig):
        super().__init__(config)
        # Simulate sensor connection
        self.connected = True

    def read(self) -> SensorReading:
        """Read formaldehyde sensor data"""
        try:
            if not self.connected:
                return self._create_error_reading("Sensor not connected")

            # Simulate reading formaldehyde concentration
            concentration = random.uniform(0.05, 0.15)  # mg/m³

            # Assess quality based on concentration
            quality_level = QualityAssessment.assess_formaldehyde(
                concentration)

            reading = SensorReading(
                sensor_id=self.config.sensor_id,
                sensor_type=self.config.sensor_type,
                timestamp=datetime.now(timezone.utc),
                values={
                    'formaldehyde_mg_m3': concentration,
                    'formaldehyde_ppm': concentration * 0.816  # Conversion factor
                },
                quality=quality_level.value,
                metadata={
                    'units': 'mg/m³',
                    'measurement_method': 'electrochemical'
                }
            )

            self.last_reading = reading
            return reading

        except Exception as e:
            logger.error(f"Error reading formaldehyde sensor: {e}")
            return self._create_error_reading(str(e))


class MockCO2Sensor(BaseSensor):
    """Mock CO2 sensor for demonstration"""

    def read(self) -> SensorReading:
        """Read CO2 sensor data"""
        try:
            ppm = random.uniform(400, 1200)  # Typical indoor range
            quality_level = QualityAssessment.assess_co2(ppm)

            reading = SensorReading(
                sensor_id=self.config.sensor_id,
                sensor_type=self.config.sensor_type,
                timestamp=datetime.now(timezone.utc),
                values={'co2_ppm': ppm},
                quality=quality_level.value,
                metadata={'units': 'ppm'}
            )

            self.last_reading = reading
            return reading

        except Exception as e:
            return self._create_error_reading(str(e))
