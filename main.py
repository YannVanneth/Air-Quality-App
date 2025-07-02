import time
from data_models import logger, SensorType, SensorConfig
from monitoring import AirQualityMonitor
from storage import InMemoryStorage
from alert import ConsoleAlertSystem, SimpleEventSystem
from sensor import FormaldehydeSensor, MockCO2Sensor


def create_sensors() -> dict:
    """Create and return a dictionary of sensors"""
    sensors = {}

    # Formaldehyde sensor
    ch2o_config = SensorConfig(
        sensor_id="ch2o_1",
        sensor_type=SensorType.FORMALDEHYDE.value,
        connection_params={"port": "/dev/ttyS0", "baudrate": 9600}
    )
    sensors["ch2o_1"] = FormaldehydeSensor(ch2o_config)

    # CO2 sensor
    co2_config = SensorConfig(
        sensor_id="co2_1",
        sensor_type=SensorType.CO2.value,
        connection_params={"port": "simulated"}
    )
    sensors["co2_1"] = MockCO2Sensor(co2_config)

    return sensors


def main():
    """Main application entry point"""
    print("🌬️  Integrated Air Quality Monitoring System")
    print("=" * 60)

    try:
        # Create system components
        sensors = create_sensors()
        storage = InMemoryStorage()
        alert_system = ConsoleAlertSystem()
        event_system = SimpleEventSystem()

        # Create monitor
        monitor = AirQualityMonitor(
            sensors=sensors,
            storage=storage,
            alert_system=alert_system,
            event_system=event_system
        )

        # Start monitoring
        monitor.start_monitoring(interval=30)
        print("✅ Monitoring started. Press Ctrl+C to stop.")
        print("\n📊 Live Data:")

        # Simple console interface
        iteration = 0
        while monitor.is_monitoring():
            time.sleep(10)
            iteration += 1

            # Print latest snapshot every 10 seconds
            snapshot = monitor.latest_snapshot
            if snapshot:
                print(
                    f"\n--- Update {iteration} ({snapshot.timestamp.strftime('%H:%M:%S')}) ---")
                print(f"🏁 Overall Quality: {snapshot.overall_quality.upper()}")

                for reading in snapshot.readings:
                    status = "✅ OK" if reading.is_valid() else "❌ ERROR"
                    primary = reading.get_primary_value()
                    if primary is not None:
                        units = "mg/m³" if "formaldehyde" in reading.sensor_type else "ppm"
                        print(f"   {reading.sensor_id}: {
                              primary:.3f} {units} - {status}")
                    else:
                        print(f"   {reading.sensor_id}: No data - {status}")

            # Print system health every 30 seconds
            if iteration % 3 == 0:
                health = monitor.get_system_health()
                print(f"\n💊 System Health: {health.health_percentage:.1f}%")
                print(f"   Healthy sensors: {
                      health.healthy_sensors}/{health.total_sensors}")
                print(f"   Uptime: {health.uptime_seconds:.0f} seconds")

    except KeyboardInterrupt:
        print("\n\n🛑 Stopping monitoring...")
    except Exception as e:
        logger.error(f"Application error: {e}")
        print(f"❌ Error: {e}")
    finally:
        if 'monitor' in locals():
            monitor.stop_monitoring()


if __name__ == "__main__":
    main()
