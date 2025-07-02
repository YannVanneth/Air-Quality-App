
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Protocol, Callable
from dataclasses import dataclass, asdict
from data_models import (
    SensorReading,
    SensorConfig,
    AirQualityLevel,
    QualityAssessment,
    AirQualitySnapshot,
    SystemHealth
)
from interfaces import (
    SensorInterface, AlertInterface, EventInterface, DataStorageInterface
)


logger = logging.getLogger('Monitoring')


class AirQualityMonitor:
    """Integrated air quality monitoring system"""

    def __init__(self, sensors, storage, alert_system, event_system):
        self.sensors = sensors
        self.storage = storage
        self.alert_system = alert_system
        self.event_system = event_system
        self.running = False
        self.thread = None
        self.latest_snapshot = None
        self.start_time = datetime.now(timezone.utc)

        # Subscribe to events
        self.event_system.subscribe(
            "sensor_reading", self._handle_sensor_reading)
        self.event_system.subscribe("sensor_error", self._handle_sensor_error)

    def start_monitoring(self, interval: int = 60) -> bool:
        """Start continuous monitoring"""
        if self.running:
            logger.warning("Monitoring already running")
            return False

        self.running = True
        self.thread = threading.Thread(
            target=self._monitoring_loop, args=(interval,))
        self.thread.daemon = True
        self.thread.start()
        logger.info(f"Started monitoring with {interval}s interval")
        return True

    def stop_monitoring(self) -> bool:
        """Stop continuous monitoring"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        logger.info("Monitoring stopped")
        return True

    def is_monitoring(self) -> bool:
        """Check if monitoring is active"""
        return self.running

    def _monitoring_loop(self, interval: int):
        """Background monitoring loop"""
        while self.running:
            try:
                snapshot = self.take_snapshot()
                self.storage.store_snapshot(snapshot)
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                self.alert_system.send_alert(
                    "system_error",
                    f"Monitoring loop failed: {e}",
                    severity="high"
                )
                time.sleep(10)  # Prevent tight error loop

    def take_snapshot(self) -> AirQualitySnapshot:
        """Take immediate air quality snapshot"""
        readings = []
        for sensor_id, sensor in self.sensors.items():
            try:
                reading = sensor.read()
                readings.append(reading)
                self.storage.store_reading(reading)
                self.event_system.emit("sensor_reading", reading)
            except Exception as e:
                logger.error(f"Error reading {sensor_id}: {e}")
                error_reading = SensorReading(
                    sensor_id=sensor_id,
                    sensor_type=sensor.get_config().sensor_type,
                    timestamp=datetime.now(timezone.utc),
                    values={},
                    quality=AirQualityLevel.ERROR.value,
                    error=str(e),
                    metadata={'error_count': getattr(sensor, 'error_count', 0)}
                )
                readings.append(error_reading)
                self.event_system.emit("sensor_error", {
                    "sensor_id": sensor_id,
                    "error": str(e)
                })

        overall_quality = QualityAssessment.get_overall_quality(readings)
        snapshot = AirQualitySnapshot(
            timestamp=datetime.now(timezone.utc),
            readings=readings,
            overall_quality=overall_quality.value
        )
        self.latest_snapshot = snapshot
        self.event_system.emit("snapshot_taken", snapshot)
        return snapshot

    def get_system_health(self) -> SystemHealth:
        """Get system health status"""
        total_sensors = len(self.sensors)
        healthy_sensors = sum(
            1 for s in self.sensors.values() if s.is_healthy())
        uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()

        return SystemHealth(
            timestamp=datetime.now(timezone.utc),
            total_sensors=total_sensors,
            healthy_sensors=healthy_sensors,
            failed_sensors=total_sensors - healthy_sensors,
            ml_model_ready=False,
            monitoring_active=self.running,
            uptime_seconds=uptime
        )

    def add_sensor(self, sensor) -> bool:
        """Add sensor to monitoring"""
        sensor_id = sensor.get_config().sensor_id
        if sensor_id in self.sensors:
            logger.warning(f"Sensor {sensor_id} already exists")
            return False

        self.sensors[sensor_id] = sensor
        logger.info(f"Added sensor {sensor_id}")
        return True

    def remove_sensor(self, sensor_id: str) -> bool:
        """Remove sensor from monitoring"""
        if sensor_id not in self.sensors:
            logger.warning(f"Sensor {sensor_id} not found")
            return False

        del self.sensors[sensor_id]
        logger.info(f"Removed sensor {sensor_id}")
        return True

    def _handle_sensor_reading(self, reading: SensorReading):
        """Handle new sensor reading event"""
        if reading.quality == AirQualityLevel.HAZARDOUS.value:
            self.alert_system.send_alert(
                "high_pollution",
                f"Hazardous level detected by {reading.sensor_id}",
                severity="critical",
                metadata=reading.to_dict()
            )

    def _handle_sensor_error(self, error_data: Dict[str, Any]):
        """Handle sensor error event"""
        sensor_id = error_data["sensor_id"]
        error = error_data["error"]
        self.alert_system.send_alert(
            "sensor_failure",
            f"Sensor {sensor_id} failed: {error}",
            severity="medium"
        )
