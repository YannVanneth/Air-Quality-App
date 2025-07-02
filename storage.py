
from datetime import timezone, datetime
from typing import Optional, Callable, Dict, Any, Tuple, List

from data_models import (
    SensorConfig,
    SensorReading,
    AirQualityLevel,
    AirQualitySnapshot,
    QualityAssessment,
    logger
)

from interfaces import CommunicationInterface


class InMemoryStorage:
    """In-memory data storage implementation"""

    def __init__(self):
        self.readings: List[SensorReading] = []
        self.snapshots: List[AirQualitySnapshot] = []

    def store_reading(self, reading: SensorReading) -> bool:
        self.readings.append(reading)
        # Keep only last 1000 readings to prevent memory issues
        if len(self.readings) > 1000:
            self.readings = self.readings[-1000:]
        return True

    def store_snapshot(self, snapshot: AirQualitySnapshot) -> bool:
        self.snapshots.append(snapshot)
        # Keep only last 100 snapshots
        if len(self.snapshots) > 100:
            self.snapshots = self.snapshots[-100:]
        return True

    def get_readings(self, sensor_id: Optional[str] = None,
                     start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None,
                     limit: Optional[int] = None) -> List[SensorReading]:
        results = []
        for reading in self.readings:
            if sensor_id and reading.sensor_id != sensor_id:
                continue
            if start_time and reading.timestamp < start_time:
                continue
            if end_time and reading.timestamp > end_time:
                continue
            results.append(reading)

        if limit:
            results = results[-limit:]
        return results

    def get_latest_reading(self, sensor_id: str) -> Optional[SensorReading]:
        for reading in reversed(self.readings):
            if reading.sensor_id == sensor_id:
                return reading
        return None

    def get_latest_snapshot(self) -> Optional[AirQualitySnapshot]:
        return self.snapshots[-1] if self.snapshots else None
