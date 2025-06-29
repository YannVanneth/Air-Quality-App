#!/usr/bin/env python3
"""
ZH07 Laser Dust Sensor Standalone Test Script
Tests ZH07 PM2.5/PM10 sensor on Raspberry Pi
"""

import pigpio
import time
import logging
import struct
from typing import Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ZH07Sensor:
    """ZH07 Laser Dust Sensor Driver"""
    
    def __init__(self, pi, rx_pin=18, tx_pin=19, baudrate=9600):
        self.pi = pi
        self.rx_pin = rx_pin
        self.tx_pin = tx_pin
        self.baudrate = baudrate
        self.bb = None
        self.last_reading = None
        
    def connect(self):
        """Connect to ZH07 sensor"""
        try:
            # Open bit-bang serial for receiving data
            self.bb = self.pi.bb_serial_read_open(self.rx_pin, self.baudrate, 8)
            logger.info(f"ZH07 connected on GPIO {self.rx_pin}")
            
            # Set working mode to passive (automatic data transmission)
            self.set_passive_mode()
            
            return True
        except Exception as e:
            logger.error(f"ZH07 connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from sensor"""
        if self.bb is not None:
            self.pi.bb_serial_read_close(self.rx_pin)
            self.bb = None
            logger.info("ZH07 disconnected")
    
    def set_passive_mode(self):
        """Set ZH07 to passive mode (auto-send data)"""
        try:
            # ZH07 passive mode command: FF 01 78 40 00 00 00 00 47
            cmd = [0xFF, 0x01, 0x78, 0x40, 0x00, 0x00, 0x00, 0x00]
            checksum = (0xFF - sum(cmd[1:]) + 1) & 0xFF
            cmd.append(checksum)
            
            # Send via software TX (if TX pin is configured)
            # For now, assume sensor is in passive mode by default
            logger.info("ZH07 set to passive mode")
            
        except Exception as e:
            logger.error(f"Failed to set passive mode: {e}")
    
    def read_raw_data(self):
        """Read raw data from sensor"""
        try:
            (count, data) = self.pi.bb_serial_read(self.rx_pin)
            return bytes(data) if count > 0 else b''
        except Exception as e:
            logger.error(f"Raw data read error: {e}")
            return b''
    
    def parse_zh07_data(self, data):
        """Parse ZH07 data frame"""
        if len(data) < 7:
            return None
        
        # Method 1: Standard ZH07 format (FF 86 PM2.5_H PM2.5_L PM10_H PM10_L CHECKSUM)
        for i in range(len(data) - 6):
            if data[i] == 0xFF and data[i+1] == 0x86:
                frame = data[i:i+7]
                
                # Verify checksum
                calculated_checksum = sum(frame[:-1]) & 0xFF
                if calculated_checksum == frame[6]:
                    pm2_5 = (frame[2] << 8) | frame[3]
                    pm10 = (frame[4] << 8) | frame[5]
                    
                    return {
                        'PM2.5': pm2_5,
                        'PM10': pm10,
                        'format': 'FF86',
                        'raw_frame': frame.hex()
                    }
        
        # Method 2: Alternative format (42 4D ... for some ZH07 variants)
        for i in range(len(data) - 12):
            if data[i] == 0x42 and data[i+1] == 0x4D:
                frame_len = (data[i+2] << 8) | data[i+3]
                if frame_len == 0x001C and i + 32 <= len(data):  # Standard PM frame length
                    frame = data[i:i+32]
                    
                    # Parse PM values (standard positions)
                    pm2_5 = (frame[6] << 8) | frame[7]
                    pm10 = (frame[8] << 8) | frame[9]
                    
                    return {
                        'PM2.5': pm2_5,
                        'PM10': pm10,
                        'format': '424D',
                        'raw_frame': frame[:12].hex()
                    }
        
        # Method 3: Simple format (AA ... for some variants)
        for i in range(len(data) - 9):
            if data[i] == 0xAA and data[i+1] == 0xC0:
                frame = data[i:i+10]
                pm2_5 = (frame[2] << 8) | frame[3]
                pm10 = (frame[4] << 8) | frame[5]
                
                return {
                    'PM2.5': pm2_5,
                    'PM10': pm10,
                    'format': 'AAC0',
                    'raw_frame': frame.hex()
                }
        
        return None
    
    def read_pm_data(self):
        """Read and parse PM data"""
        try:
            raw_data = self.read_raw_data()
            
            if raw_data:
                result = self.parse_zh07_data(raw_data)
                if result:
                    self.last_reading = result
                    result['timestamp'] = time.time()
                    return result
            
            return None
            
        except Exception as e:
            logger.error(f"PM data read error: {e}")
            return None
    
    def get_air_quality_index(self, pm2_5, pm10):
        """Calculate simple air quality index"""
        # Simplified AQI calculation
        if pm2_5 <= 12 and pm10 <= 54:
            return "Good", "green"
        elif pm2_5 <= 35 and pm10 <= 154:
            return "Moderate", "yellow"
        elif pm2_5 <= 55 and pm10 <= 254:
            return "Unhealthy for Sensitive Groups", "orange"
        elif pm2_5 <= 150 and pm10 <= 354:
            return "Unhealthy", "red"
        else:
            return "Very Unhealthy", "purple"
    
    def display_data(self, data):
        """Display formatted sensor data"""
        if not data:
            print("No data received")
            return
        
        pm2_5 = data['PM2.5']
        pm10 = data['PM10']
        format_type = data.get('format', 'unknown')
        
        # Get air quality assessment
        aqi_status, aqi_color = self.get_air_quality_index(pm2_5, pm10)
        
        print(f"ZH07 Reading [{format_type}]: PM2.5={pm2_5:3d}μg/m³, PM10={pm10:3d}μg/m³ - {aqi_status}")
        
        # Show raw frame for debugging
        if 'raw_frame' in data:
            print(f"Raw frame: {data['raw_frame']}")

def test_zh07():
    """Test ZH07 sensor"""
    print("=== ZH07 Laser Dust Sensor Test ===")
    print("Starting pigpio daemon if needed...")
    
    # Initialize pigpio
    pi = pigpio.pi()
    if not pi.connected:
        print("Failed to connect to pigpio daemon")
        print("Run: sudo pigpiod")
        return
    
    # Create sensor instance
    sensor = ZH07Sensor(pi, rx_pin=18, tx_pin=19)
    
    if not sensor.connect():
        print("Failed to connect to ZH07 sensor")
        pi.stop()
        return
    
    print("ZH07 connected successfully!")
    print("Waiting for data... (ZH07 sends data every 1-2 seconds)")
    print("Press Ctrl+C to stop")
    print("-" * 60)
    
    try:
        sample_count = 0
        no_data_count = 0
        
        while True:
            data = sensor.read_pm_data()
            sample_count += 1
            
            if data:
                print(f"Sample {sample_count:3d}: ", end="")
                sensor.display_data(data)
                no_data_count = 0
            else:
                no_data_count += 1
                if no_data_count % 10 == 0:
                    print(f"No data for {no_data_count} attempts - checking connections...")
                    
                    # Show raw data for debugging
                    raw = sensor.read_raw_data()
                    if raw:
                        print(f"Raw data received: {raw.hex()}")
                    else:
                        print("No raw data received")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nTest stopped by user")
    except Exception as e:
        print(f"Test error: {e}")
    finally:
        sensor.disconnect()
        pi.stop()

def debug_zh07():
    """Debug mode for ZH07 - shows all raw data"""
    print("=== ZH07 Debug Mode ===")
    
    pi = pigpio.pi()
    if not pi.connected:
        print("Failed to connect to pigpio daemon")
        return
    
    sensor = ZH07Sensor(pi, rx_pin=18)
    
    if not sensor.connect():
        print("Failed to connect to ZH07")
        pi.stop()
        return
    
    print("Debug mode - showing all raw data")
    print("Press Ctrl+C to stop")
    print("-" * 40)
    
    try:
        while True:
            raw_data = sensor.read_raw_data()
            
            if raw_data:
                print(f"Raw: {raw_data.hex()}")
                
                # Try to parse
                parsed = sensor.parse_zh07_data(raw_data)
                if parsed:
                    print(f"Parsed: PM2.5={parsed['PM2.5']}, PM10={parsed['PM10']}")
                
                print("-" * 40)
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\nDebug stopped")
    finally:
        sensor.disconnect()
        pi.stop()

if __name__ == "__main__":
    print("ZH07 Test Options:")
    print("1. Normal test")
    print("2. Debug mode (raw data)")
    
    try:
        choice = input("Enter choice (1 or 2): ").strip()
        
        if choice == "2":
            debug_zh07()
        else:
            test_zh07()
            
    except KeyboardInterrupt:
        print("\nProgram terminated")
    except Exception as e:
        print(f"Program error: {e}")
