#!/usr/bin/env python3
"""
Comprehensive Air Quality Monitoring System
Integrates multiple sensors for formaldehyde, CO2, particulate matter, and gas detection
"""

import time
import serial
import logging
import csv
from datetime import datetime
from enum import Enum
from typing import Dict, Optional, Tuple, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("air_quality_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Air Quality Level Enums


class AirQualityLevel(Enum):
    EXCELLENT = 0
    GOOD = 1
    MODERATE = 2
    POOR = 3
    UNHEALTHY = 4
    HAZARDOUS = 5


class FormaldehydeSensor:
    """ZE08-CH2O Formaldehyde Sensor Interface"""

    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self) -> bool:
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=2
            )
            logger.info(f"Formaldehyde sensor connected on {self.port}")
            time.sleep(1)  # Allow sensor to initialize
            self._set_active_mode()
            return True
        except Exception as e:
            logger.error(f"Formaldehyde sensor connection failed: {e}")
            return False

    def _calculate_checksum(self, data: List[int]) -> int:
        checksum = sum(data) & 0xFF
        return ((~checksum) + 1) & 0xFF

    def _set_active_mode(self):
        """Set sensor to active upload mode"""
        try:
            command = bytearray(
                [0xFF, 0x01, 0x78, 0x40, 0x00, 0x00, 0x00, 0x00])
            checksum = self._calculate_checksum(command[1:8])
            command.append(checksum)
            self.ser.write(command)
            time.sleep(0.5)
            logger.info("Formaldehyde sensor set to active mode")
        except Exception as e:
            logger.error(f"Error setting active mode: {e}")

    def read(self) -> Optional[Dict[str, float]]:
        if not self.ser or not self.ser.is_open:
            return None

        try:
            # Clear buffer and wait for data
            self.ser.reset_input_buffer()
            start_time = time.time()

            while time.time() - start_time < 3:  # Wait up to 3 seconds
                if self.ser.in_waiting >= 9:
                    response = self.ser.read(9)

                    if len(response) == 9 and response[0] == 0xFF and response[1] == 0x17:
                        # Validate unit is ppb (0x04 = ppb)
                        if response[2] == 0x04:
                            # Extract concentration (bytes 4-5)
                            conc_high = response[4]
                            conc_low = response[5]
                            ppb = (conc_high << 8) | conc_low

                            # Convert to other units
                            ppm = ppb / 1000.0
                            mg_m3 = ppm * 1.25  # Conversion factor

                            return {
                                'ppb': ppb,
                                'ppm': ppm,
                                'mg_m3': mg_m3
                            }
                time.sleep(0.1)

            logger.warning("No valid formaldehyde data received")
            return None

        except Exception as e:
            logger.error(f"Error reading formaldehyde sensor: {e}")
            return None

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Formaldehyde sensor connection closed")


class CO2Sensor:
    """MH-Z19 CO2 Sensor Interface"""

    def __init__(self, port: str = '/dev/ttyS0', baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self) -> bool:
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=2
            )
            logger.info(f"CO2 sensor connected on {self.port}")
            time.sleep(1)  # Allow sensor to initialize
            return True
        except Exception as e:
            logger.error(f"CO2 sensor connection failed: {e}")
            return False

    def read(self) -> Optional[Dict[str, float]]:
        if not self.ser or not self.ser.is_open:
            return None

        try:
            # Send read command
            cmd = bytearray(
                [0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79])
            self.ser.write(cmd)
            time.sleep(0.2)

            # Read response
            if self.ser.in_waiting >= 9:
                response = self.ser.read(9)

                if len(response) == 9 and response[0] == 0xFF and response[1] == 0x86:
                    co2 = (response[2] << 8) | response[3]
                    temperature = response[4] - 40  # Sensor returns temp + 40

                    return {
                        'co2_ppm': co2,
                        'temperature': temperature
                    }

            logger.warning("No valid CO2 data received")
            return None

        except Exception as e:
            logger.error(f"Error reading CO2 sensor: {e}")
            return None

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("CO2 sensor connection closed")


class ParticleSensor:
    """ZH07 Particle Matter Sensor Interface"""

    def __init__(self, port: str = '/dev/ttyAMA0', baudrate: int = 9600):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def connect(self) -> bool:
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=2
            )
            logger.info(f"Particle sensor connected on {self.port}")
            time.sleep(1)  # Allow sensor to initialize
            return True
        except Exception as e:
            logger.error(f"Particle sensor connection failed: {e}")
            return False

    def read(self) -> Optional[Dict[str, float]]:
        if not self.ser or not self.ser.is_open:
            return None

        try:
            # Clear buffer
            self.ser.reset_input_buffer()

            # Send read command
            request_frame = bytearray(
                [0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79])
            self.ser.write(request_frame)
            time.sleep(0.1)

            # Read response
            data = self.ser.read(9)

            if len(data) == 9 and data[0] == 0xFF and data[1] == 0x18:
                pm2_5 = (data[2] << 8) | data[3]
                pm10 = (data[4] << 8) | data[5]

                return {
                    'pm2_5': pm2_5,
                    'pm10': pm10
                }

            logger.warning("No valid particle data received")
            return None

        except Exception as e:
            logger.error(f"Error reading particle sensor: {e}")
            return None

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Particle sensor connection closed")


class AirQualityMonitor:
    """Main Air Quality Monitoring System"""

    def __init__(self):
        self.formaldehyde_sensor = FormaldehydeSensor()
        self.co2_sensor = CO2Sensor()
        self.particle_sensor = ParticleSensor()
        self.csv_file = "air_quality_data.csv"
        self.initialize_csv()

    def initialize_csv(self):
        """Create CSV file with headers if it doesn't exist"""
        try:
            with open(self.csv_file, 'x') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'hcho_ppb', 'hcho_ppm', 'hcho_mg_m3',
                    'co2_ppm', 'temperature',
                    'pm2_5', 'pm10',
                    'air_quality_level'
                ])
            logger.info(f"Created new data file: {self.csv_file}")
        except FileExistsError:
            pass  # File already exists, no need to create

    def connect_sensors(self) -> bool:
        """Connect to all sensors"""
        success = True

        if not self.formaldehyde_sensor.connect():
            success = False
        if not self.co2_sensor.connect():
            success = False
        if not self.particle_sensor.connect():
            success = False

        return success

    def calculate_air_quality(
        self,
        hcho_mg_m3: float,
        co2_ppm: float,
        pm2_5: float
    ) -> AirQualityLevel:
        """Determine overall air quality level based on sensor readings"""
        # Formaldehyde thresholds (mg/m³)
        if hcho_mg_m3 < 0.08:
            hcho_level = 0
        elif hcho_mg_m3 < 0.1:
            hcho_level = 1
        elif hcho_mg_m3 < 0.12:
            hcho_level = 2
        elif hcho_mg_m3 < 0.16:
            hcho_level = 3
        else:
            hcho_level = 4

        # CO2 thresholds (ppm)
        if co2_ppm < 800:
            co2_level = 0
        elif co2_ppm < 1000:
            co2_level = 1
        elif co2_ppm < 1500:
            co2_level = 2
        elif co2_ppm < 2000:
            co2_level = 3
        else:
            co2_level = 4

        # PM2.5 thresholds (μg/m³)
        if pm2_5 < 12:
            pm_level = 0
        elif pm2_5 < 35:
            pm_level = 1
        elif pm2_5 < 55:
            pm_level = 2
        elif pm2_5 < 150:
            pm_level = 3
        else:
            pm_level = 4

        # Weighted average (can adjust weights based on importance)
        weighted_score = (hcho_level * 0.4) + \
            (co2_level * 0.4) + (pm_level * 0.2)

        # Determine overall air quality level
        if weighted_score < 1:
            return AirQualityLevel.EXCELLENT
        elif weighted_score < 2:
            return AirQualityLevel.GOOD
        elif weighted_score < 3:
            return AirQualityLevel.MODERATE
        elif weighted_score < 4:
            return AirQualityLevel.POOR
        else:
            return AirQualityLevel.UNHEALTHY

    def read_sensors(self) -> Dict[str, float]:
        """Read data from all sensors"""
        data = {'timestamp': datetime.now().isoformat()}

        # Read formaldehyde sensor
        hcho_data = self.formaldehyde_sensor.read()
        if hcho_data:
            data.update({
                'hcho_ppb': hcho_data.get('ppb', 0),
                'hcho_ppm': hcho_data.get('ppm', 0),
                'hcho_mg_m3': hcho_data.get('mg_m3', 0)
            })

        # Read CO2 sensor
        co2_data = self.co2_sensor.read()
        if co2_data:
            data.update({
                'co2_ppm': co2_data.get('co2_ppm', 0),
                'temperature': co2_data.get('temperature', 0)
            })

        # Read particle sensor
        particle_data = self.particle_sensor.read()
        if particle_data:
            data.update({
                'pm2_5': particle_data.get('pm2_5', 0),
                'pm10': particle_data.get('pm10', 0)
            })

        # Calculate air quality level
        if 'hcho_mg_m3' in data and 'co2_ppm' in data and 'pm2_5' in data:
            aq_level = self.calculate_air_quality(
                data['hcho_mg_m3'],
                data['co2_ppm'],
                data['pm2_5']
            )
            data['air_quality_level'] = aq_level.name

        return data

    def log_data(self, data: Dict):
        """Log data to CSV file"""
        try:
            with open(self.csv_file, 'a') as f:
                writer = csv.writer(f)
                writer.writerow([
                    data.get('timestamp', ''),
                    data.get('hcho_ppb', 0),
                    data.get('hcho_ppm', 0),
                    data.get('hcho_mg_m3', 0),
                    data.get('co2_ppm', 0),
                    data.get('temperature', 0),
                    data.get('pm2_5', 0),
                    data.get('pm10', 0),
                    data.get('air_quality_level', 'UNKNOWN')
                ])
        except Exception as e:
            logger.error(f"Error logging data: {e}")

    def display_data(self, data: Dict):
        """Display data in a human-readable format"""
        print("\n" + "=" * 50)
        print(f"AIR QUALITY REPORT - {data.get('timestamp', '')}")
        print("=" * 50)

        if 'hcho_ppb' in data:
            print(f"Formaldehyde: {data['hcho_ppb']:.0f} ppb ({data['hcho_ppm']:.3f} ppm)")

        if 'co2_ppm' in data:
            print(f"CO₂: {data['co2_ppm']:.0f} ppm")

        if 'temperature' in data:
            print(f"Temperature: {data['temperature']:.1f}°C")

        if 'pm2_5' in data:
            print(f"Particulate Matter: PM2.5 = {
                  data['pm2_5']} μg/m³, PM10 = {data['pm10']} μg/m³")

        if 'air_quality_level' in data:
            level = data['air_quality_level']
            print(f"\nOVERALL AIR QUALITY: {level}")

            # Add emoji for visual indication
            if level == "EXCELLENT":
                print("✅ Excellent air quality")
            elif level == "GOOD":
                print("👍 Good air quality")
            elif level == "MODERATE":
                print("⚠️  Moderate air quality")
            elif level == "POOR":
                print("⚠️  Poor air quality - consider ventilation")
            elif level == "UNHEALTHY":
                print("❌ Unhealthy air quality - take action")
            elif level == "HAZARDOUS":
                print("⛔ Hazardous air quality - evacuate area")

        print("=" * 50 + "\n")

    def close(self):
        """Close all sensor connections"""
        self.formaldehyde_sensor.close()
        self.co2_sensor.close()
        self.particle_sensor.close()
        logger.info("All sensor connections closed")


def main():
    """Main monitoring loop"""
    monitor = AirQualityMonitor()

    if not monitor.connect_sensors():
        logger.error("Failed to connect to one or more sensors. Exiting.")
        return

    print("Air Quality Monitoring System Started")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            # Read all sensors
            sensor_data = monitor.read_sensors()

            if sensor_data:
                # Log and display the data
                monitor.log_data(sensor_data)
                monitor.display_data(sensor_data)

            # Wait before next reading
            time.sleep(30)  # Read every 30 seconds

    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
    finally:
        monitor.close()


if __name__ == "__main__":
    main()
