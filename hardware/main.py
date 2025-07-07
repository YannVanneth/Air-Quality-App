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

logger = logging.getLogger(__name__)

def create_sensor_reading_dict(reading):
    """Convert sensor reading to dictionary format"""
    if hasattr(reading, 'to_dict'):
        return reading.to_dict()
    
    # Fallback for custom reading format
    return {
        'sensor_id': getattr(reading, 'sensor_id', 'unknown'),
        'timestamp': getattr(reading, 'timestamp', datetime.now()).isoformat(),
        'data': getattr(reading, 'data', {}),
        'status': str(getattr(reading, 'status', 'unknown')),
        'quality': str(getattr(reading, 'quality', 'unknown'))
    }

def validate_sensor_reading(reading):
    """Validate sensor reading data"""
    if not reading:
        return False
    
    # Check if reading has required attributes
    required_attrs = ['sensor_id', 'timestamp', 'data']
    return all(hasattr(reading, attr) for attr in required_attrs)

def log_sensor_status(sensors):
    """Log the status of all sensors"""
    for sensor in sensors:
        try:
            status = sensor.get_status()
            logger.info(f"Sensor {sensor.sensor_id}: {status}")
        except Exception as e:
            logger.error(f"Error getting status for {sensor.sensor_id}: {e}")

def main():
    logger.info("Starting Air Quality Monitoring System")
    
    # Initialize sensors
    sensors = [
        ZCE04BSensor(port='/dev/ttyUSB0', sensor_id="GAS_SENSOR_01"),
        ZH07(port='/dev/ttyUSB1', sensor_id="PM_SENSOR_01", baud_rate=9600)
    ]
    
    # Connect to sensors
    connected_sensors = []
    for sensor in sensors:
        try:
            if sensor.connect():
                connected_sensors.append(sensor)
                logger.info(f"Successfully connected to {sensor.sensor_id}")
            else:
                logger.error(f"Failed to connect to {sensor.sensor_id}")
        except Exception as e:
            logger.error(f"Exception connecting to {sensor.sensor_id}: {e}")
    
    if not connected_sensors:
        logger.error("No sensors connected. Exiting.")
        return
    
    logger.info(f"Connected to {len(connected_sensors)} out of {len(sensors)} sensors")
    
    # Main monitoring loop
    cycle_count = 0
    consecutive_failures = {sensor.sensor_id: 0 for sensor in connected_sensors}
    
    try:
        while True:
            cycle_count += 1
            readings = []
            start_time = time.time()
            
            logger.debug(f"Starting monitoring cycle {cycle_count}")
            
            # Read from each sensor
            for sensor in connected_sensors:
                try:
                    # All sensors now implement the standard read_data() method
                    reading = sensor.read_data()
                    
                    if reading and validate_sensor_reading(reading):
                        readings.append(reading)
                        consecutive_failures[sensor.sensor_id] = 0
                        logger.debug(f"Successfully read from {sensor.sensor_id}")
                    else:
                        consecutive_failures[sensor.sensor_id] += 1
                        logger.warning(f"No valid data from {sensor.sensor_id} "
                                     f"(failures: {consecutive_failures[sensor.sensor_id]})")
                        
                except Exception as e:
                    consecutive_failures[sensor.sensor_id] += 1
                    logger.error(f"Error reading from {sensor.sensor_id}: {e}")
                    
                    # Try to reconnect if too many failures
                    if consecutive_failures[sensor.sensor_id] >= 5:
                        logger.warning(f"Attempting to reconnect to {sensor.sensor_id}")
                        try:
                            sensor.disconnect()
                            time.sleep(1)
                            if sensor.connect():
                                consecutive_failures[sensor.sensor_id] = 0
                                logger.info(f"Successfully reconnected to {sensor.sensor_id}")
                            else:
                                logger.error(f"Failed to reconnect to {sensor.sensor_id}")
                        except Exception as reconnect_e:
                            logger.error(f"Exception during reconnect to {sensor.sensor_id}: {reconnect_e}")
            
            # Process and output readings
            if readings:
                logger.info(f"Cycle {cycle_count}: Collected {len(readings)} readings")
                
                for reading in readings:
                    try:
                        reading_dict = create_sensor_reading_dict(reading)
                        
                        # Print formatted JSON
                        print(json.dumps(reading_dict, indent=2, default=str))
                        print("-" * 50)  # Separator line
                        
                        # Log summary
                        sensor_id = reading_dict.get('sensor_id', 'unknown')
                        data_keys = list(reading_dict.get('data', {}).keys())
                        logger.info(f"{sensor_id}: {', '.join(data_keys)}")
                        
                    except Exception as e:
                        logger.error(f"Error processing reading: {e}")
            else:
                logger.warning(f"Cycle {cycle_count}: No readings collected")
            
            # Log sensor status periodically
            if cycle_count % 10 == 0:
                log_sensor_status(connected_sensors)
            
            # Maintain consistent cycle time
            processing_time = time.time() - start_time
            sleep_time = max(0, 5.0 - processing_time)
            
            logger.debug(f"Cycle {cycle_count} completed in {processing_time:.2f}s, "
                        f"sleeping for {sleep_time:.2f}s")
            
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
    finally:
        logger.info("Disconnecting sensors...")
        for sensor in connected_sensors:
            try:
                sensor.disconnect()
                logger.info(f"Disconnected {sensor.sensor_id}")
            except Exception as e:
                logger.error(f"Error disconnecting {sensor.sensor_id}: {e}")
        
        logger.info("System shutdown complete")

if __name__ == "__main__":
    main()
