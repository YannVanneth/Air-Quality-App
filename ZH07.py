
import serial
import json
import time
from datetime import datetime

def parse_zh07_data(raw_bytes):
    """
    Parse raw ZH07 sensor bytes and return structured data
    """
    if len(raw_bytes) < 9:
        return None
    
    # Convert bytes to list for JSON serialization
    raw_data = list(raw_bytes)
    
    # Basic packet structure
    packet_data = {
        "timestamp": datetime.now().isoformat(),
        "raw_bytes": raw_data,
        "raw_hex": [f"0x{b:02X}" for b in raw_bytes],
        "packet_length": len(raw_bytes),
        "header": {
            "byte1": raw_data[0],
            "byte2": raw_data[1],
            "hex": f"0x{raw_data[0]:02X}{raw_data[1]:02X}",
            "valid": raw_data[0] == 0x42 and raw_data[1] == 0x4D
        }
    }
    
    # If valid header, parse sensor data
    if packet_data["header"]["valid"]:
        # Extract PM values (adjust positions based on your sensor model)
        pm25_raw = (raw_data[2] << 8) | raw_data[3]
        pm10_raw = (raw_data[4] << 8) | raw_data[5]
        
        # Calculate checksum
        calculated_checksum = sum(raw_data[0:8]) % 256
        received_checksum = raw_data[8]
        
        packet_data["sensor_data"] = {
            "pm25": {
                "raw_value": pm25_raw,
                "value": pm25_raw,  # Adjust if needed (e.g., divide by 10)
                "unit": "μg/m³",
                "bytes": [raw_data[2], raw_data[3]],
                "hex": f"0x{raw_data[2]:02X}{raw_data[3]:02X}"
            },
            "pm10": {
                "raw_value": pm10_raw,
                "value": pm10_raw,  # Adjust if needed (e.g., divide by 10)
                "unit": "μg/m³",
                "bytes": [raw_data[4], raw_data[5]],
                "hex": f"0x{raw_data[4]:02X}{raw_data[5]:02X}"
            },
            "additional_bytes": {
                "byte6": {"value": raw_data[6], "hex": f"0x{raw_data[6]:02X}"},
                "byte7": {"value": raw_data[7], "hex": f"0x{raw_data[7]:02X}"}
            },
            "checksum": {
                "calculated": calculated_checksum,
                "received": received_checksum,
                "valid": calculated_checksum == received_checksum,
                "hex": f"0x{received_checksum:02X}"
            }
        }
        
        # Air quality assessment
        packet_data["air_quality"] = assess_air_quality(pm25_raw, pm10_raw)
    else:
        packet_data["error"] = "Invalid header - expected 'BM' (0x42 0x4D)"
    
    return packet_data

def assess_air_quality(pm25, pm10):
    """
    Assess air quality based on WHO guidelines and common standards
    """
    # WHO guidelines and common AQI breakpoints
    pm25_levels = [
        (0, 12, "Good"),
        (12, 35, "Moderate"),
        (35, 55, "Unhealthy for Sensitive Groups"),
        (55, 150, "Unhealthy"),
        (150, 250, "Very Unhealthy"),
        (250, float('inf'), "Hazardous")
    ]
    
    pm10_levels = [
        (0, 20, "Good"),
        (20, 50, "Moderate"),
        (50, 100, "Unhealthy for Sensitive Groups"),
        (100, 200, "Unhealthy"),
        (200, 300, "Very Unhealthy"),
        (300, float('inf'), "Hazardous")
    ]
    
    def get_level(value, levels):
        for min_val, max_val, level in levels:
            if min_val <= value < max_val:
                return level
        return "Unknown"
    
    return {
        "pm25_level": get_level(pm25, pm25_levels),
        "pm10_level": get_level(pm10, pm10_levels),
        "overall_assessment": "Needs attention" if pm25 > 35 or pm10 > 100 else "Acceptable"
    }

def read_and_convert_to_json(ser, output_file=None, pretty_print=True):
    """
    Read sensor data and convert to JSON format
    """
    readings = []
    
    try:
        while True:
            if ser.in_waiting >= 9:
                raw_bytes = ser.read(9)
                
                # Parse the data
                parsed_data = parse_zh07_data(raw_bytes)
                
                if parsed_data:
                    # Add to readings list
                    readings.append(parsed_data)
                    
                    # Print JSON to console
                    if pretty_print:
                        print(json.dumps(parsed_data, indent=2))
                        print("-" * 50)
                    else:
                        print(json.dumps(parsed_data))
                    
                    # Save to file if specified
                    if output_file:
                        with open(output_file, 'w') as f:
                            json.dump(readings, f, indent=2)
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print(f"\nCaptured {len(readings)} readings")
        return readings

def convert_raw_bytes_to_json(raw_bytes_list):
    """
    Convert a list of raw byte arrays to JSON (for batch processing)
    """
    results = []
    
    for i, raw_bytes in enumerate(raw_bytes_list):
        if isinstance(raw_bytes, str):
            # If hex string, convert to bytes
            raw_bytes = bytes.fromhex(raw_bytes.replace('0x', '').replace(' ', ''))
        elif isinstance(raw_bytes, list):
            # If list of integers, convert to bytes
            raw_bytes = bytes(raw_bytes)
        
        parsed = parse_zh07_data(raw_bytes)
        if parsed:
            parsed["reading_number"] = i + 1
            results.append(parsed)
    
    return results

def main():
    """
    Main function - can be used for live reading or batch processing
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Convert ZH07 sensor data to JSON')
    parser.add_argument('--live', action='store_true', help='Read live data from sensor')
    parser.add_argument('--port', default='/dev/serial0', help='Serial port (default: /dev/serial0)')
    parser.add_argument('--output', help='Output JSON file')
    parser.add_argument('--test', action='store_true', help='Test with sample data')
    
    args = parser.parse_args()
    
    if args.test:
        # Test with sample raw bytes
        sample_data = [
            [0x42, 0x4D, 0x00, 0x1C, 0x00, 0x20, 0x00, 0x00, 0x88],  # Sample valid packet
            [0x42, 0x4D, 0x00, 0x0F, 0x00, 0x15, 0x00, 0x00, 0x7B],  # Another sample
            [0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]   # Invalid header
        ]
        
        results = convert_raw_bytes_to_json(sample_data)
        print(json.dumps(results, indent=2))
        
    elif args.live:
        try:
            ser = serial.Serial(args.port, 9600, timeout=1)
            print(f"Reading live data from {args.port}")
            print("Press Ctrl+C to stop")
            ser.reset_input_buffer()
            
            read_and_convert_to_json(ser, args.output)
            
        except serial.SerialException as e:
            print(f"Serial error: {e}")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if 'ser' in locals() and ser.is_open:
                ser.close()
    else:
        print("Use --live for live reading or --test for sample data")
        print("Example: python script.py --live --output readings.json")

if __name__ == '__main__':
    main()
