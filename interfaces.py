import time
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Protocol, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from data_models import (
    SensorReading,
    SensorConfig,
    AirQualityLevel,
    AirQualitySnapshot,
    SystemHealth
)


class SensorInterface(Protocol):
    """Protocol for all sensor implementations"""

    def read(self) -> SensorReading:
        """Read sensor data and return standardized reading"""
        ...

    def get_sensor_info(self) -> Dict[str, str]:
        """Get sensor metadata and status"""
        ...

    def is_healthy(self) -> bool:
        """Check if sensor is functioning properly"""
        ...

    def get_config(self) -> SensorConfig:
        """Get sensor configuration"""
        ...


class DataStorageInterface(Protocol):
    """Protocol for data storage backends"""

    def store_reading(self, reading: SensorReading) -> bool:
        """Store a single sensor reading"""
        ...

    def store_snapshot(self, snapshot: AirQualitySnapshot) -> bool:
        """Store complete air quality snapshot"""
        ...

    def get_readings(self, **filters) -> List[SensorReading]:
        """Retrieve readings with optional filtering"""
        ...

    def get_latest_reading(self, sensor_id: str) -> Optional[SensorReading]:
        """Get the most recent reading for a sensor"""
        ...

    def get_latest_snapshot(self) -> Optional[AirQualitySnapshot]:
        """Get the most recent air quality snapshot"""
        ...


class AlertInterface(Protocol):
    """Protocol for alert and notification systems"""

    def send_alert(self, alert_type: str, message: str, severity: str = "medium",
                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Send an alert"""
        ...

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get currently active alerts"""
        ...


class EventInterface(Protocol):
    """Protocol for event handling"""

    def subscribe(self, event_type: str, callback: Callable) -> str:
        """Subscribe to events, return subscription ID"""
        ...

    def emit(self, event_type: str, data: Any) -> bool:
        """Emit an event"""
        ...


class MonitoringInterface(Protocol):
    """Protocol for system monitoring"""

    def start_monitoring(self, interval: int = 60) -> bool:
        """Start continuous monitoring"""
        ...

    def stop_monitoring(self) -> bool:
        """Stop monitoring"""
        ...

    def is_monitoring(self) -> bool:
        """Check if monitoring is active"""
        ...

    def get_system_health(self) -> SystemHealth:
        """Get system health status"""
        ...

    def take_snapshot(self) -> AirQualitySnapshot:
        """Take immediate air quality snapshot"""
        ...

    def add_sensor(self, sensor: SensorInterface) -> bool:
        """Add sensor to monitoring"""
        ...


class CommunicationInterface(Protocol):
    """Protocol for sensor communication"""

    def connect(self, connection_params: Dict[str, Any]) -> bool:
        """Establish connection to sensor"""
        ...

    def is_connected(self) -> bool:
        """Check if connected to sensor"""
        ...

    def read_data(self, timeout: float = 1.0) -> bytes:
        """Read data from sensor"""
        ...
