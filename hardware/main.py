

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

    try:
        while True:
            readings = []

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


if __name__ == "__main__":
    main()

