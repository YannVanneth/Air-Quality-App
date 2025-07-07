import logging
import time
import json
from datetime import datetime
from MultiGas import ZCE04BSensor
from ParticulateMatter import ZH07

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("sensor_monitor.log"),
        logging.StreamHandler()
    ]
)


def main():
    logging.info("Starting Air Quality Monitoring System")

    sensors = [
        ZCE04BSensor(port='/dev/ttyS0', sensor_id="GAS_SENSOR_01"),
       # ZH07(port='/dev/ttyUSB0', sensor_id="PM_SENSOR_01", baud_rate=9600)
    ]

    for sensor in sensors:
        if not sensor.connect():
            logging.error(f"Failed to connect to {sensor.sensor_id}")

    try:
        while True:
            readings = []
            start_time = time.time()

            for sensor in sensors:
                try:
                    if reading := sensor.read_data():
                        readings.append(reading)
                        logging.info(f"Read from {sensor.sensor_id}")
                except Exception as e:
                    logging.error(f"Error reading {sensor.sensor_id}: {e}")

            # Process and output readings
            for reading in readings:
                print(json.dumps(reading.to_dict(), indent=2))

            # Maintain consistent cycle time
            processing_time = time.time() - start_time
            sleep_time = max(0, 5.0 - processing_time)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logging.info("Shutdown requested")
    finally:
        logging.info("Disconnecting sensors...")
        for sensor in sensors:
            sensor.disconnect()
        logging.info("System shutdown complete")


if __name__ == "__main__":
    main()
