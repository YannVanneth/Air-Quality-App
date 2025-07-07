<<<<<<< HEAD


import logging
import time
import json
import signal
import sys
from datetime import datetime
from typing import List, Dict, Any
from MultiGas import ZCE04BSensor

def main():
    logging.info("Starting air quality monitoring system on Raspberry Pi...")
    zce04b = ZCE04BSensor(port='/dev/ttyUSB0')
 #   zh07 = ZH07Sensor(port='/dev/ttyS0')
 #   zp07 = ZP07Sensor(warm_up_time=10)

    zce04b.connect()
    time.sleep(1)
 #   zh07.connect()
    #zp07.connect()
=======
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
        ZCE04BSensor(port='/dev/ttyUSB0', sensor_id="GAS_SENSOR_01"),
        # ZH07(port='/dev/ttyUSB0', sensor_id="PM_SENSOR_01", baud_rate=9600)
    ]

    for sensor in sensors:
        if not sensor.connect():
            logging.error(f"Failed to connect to {sensor.sensor_id}")
>>>>>>> bb2ccc373fbcc4c5633ff95ef34553c205043db8

    try:
        while True:
            readings = []
<<<<<<< HEAD

            zce04b_reading = zce04b.read_data()
            if zce04b_reading:
                readings.append(zce04b_reading)
#
#            zh07_reading = zh07.read_data()
#            if zh07_reading:
#                readings.append(zh07_reading)
#
#            zp07_reading = zp07.read_data()
#            if zp07_reading:
#                readings.append(zp07_reading)
#
            for reading in readings:
                print(json.dumps(reading.to_dict(), indent=2))

            time.sleep(5)
    except Exception as e:
        logging.info(f"{e}")

    finally:
        zce04b.disconnect()
#        zh07.disconnect()
#        zp07.disconnect()
        logging.info("System shut down.")
=======
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
>>>>>>> bb2ccc373fbcc4c5633ff95ef34553c205043db8


if __name__ == "__main__":
    main()

