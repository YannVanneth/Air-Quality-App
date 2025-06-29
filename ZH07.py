



import serial
import time

def debug_zh07_header(ser, num_readings=10):
    """
    Debug tool to analyze ZH07 header issues
    """
    print("ZH07 Header Debug Tool")
    print("=" * 50)
    print("Expected header: 'BM' (0x42 0x4D)")
    print("Analyzing incoming data...\n")
    
    readings_count = 0
    all_data = []
    
    while readings_count < num_readings:
        if ser.in_waiting > 0:
            # Read all available bytes
            available_bytes = ser.in_waiting
            data = ser.read(available_bytes)
            all_data.extend(data)
            
            print(f"Reading {readings_count + 1}:")
            print(f"  Available bytes: {available_bytes}")
            print(f"  Raw bytes: {list(data)}")
            print(f"  Hex: {[f'0x{b:02X}' for b in data]}")
            print(f"  ASCII: {[chr(b) if 32 <= b <= 126 else '.' for b in data]}")
            
            # Look for potential headers in the data
            for i in range(len(data) - 1):
                if data[i] == 0x42 and data[i+1] == 0x4D:
                    print(f"  ✓ Found 'BM' header at position {i}")
                elif data[i] == 0x4D and data[i+1] == 0x42:
                    print(f"  ? Found 'MB' (reversed) at position {i}")
            
            print()
            readings_count += 1
            
        time.sleep(0.5)
    
    # Analyze all collected data
    print("\nFull Data Analysis:")
    print("=" * 50)
    print(f"Total bytes collected: {len(all_data)}")
    print(f"All data: {list(all_data)}")
    print(f"All hex: {[f'0x{b:02X}' for b in all_data]}")
    
    # Look for patterns
    print("\nPattern Analysis:")
    bm_positions = []
    for i in range(len(all_data) - 1):
        if all_data[i] == 0x42 and all_data[i+1] == 0x4D:
            bm_positions.append(i)
    
    if bm_positions:
        print(f"Found 'BM' headers at positions: {bm_positions}")
        
        # Check if we can extract 9-byte packets
        for pos in bm_positions:
            if pos + 8 < len(all_data):
                packet = all_data[pos:pos+9]
                print(f"\nPacket starting at position {pos}:")
                print(f"  Bytes: {packet}")
                print(f"  Hex: {[f'0x{b:02X}' for b in packet]}")
                
                # Check checksum
                calculated_checksum = sum(packet[0:8]) % 256
                received_checksum = packet[8]
                checksum_valid = calculated_checksum == received_checksum
                
                print(f"  Checksum: Calc=0x{calculated_checksum:02X}, Recv=0x{received_checksum:02X}, Valid={checksum_valid}")
                
                # Extract PM values
                pm25 = (packet[2] << 8) | packet[3]
                pm10 = (packet[4] << 8) | packet[5]
                print(f"  PM2.5: {pm25}, PM10: {pm10}")
    else:
        print("No 'BM' headers found!")
        
        # Check for other common patterns
        common_headers = [
            (0xFF, 0xFF, "0xFF 0xFF"),
            (0x00, 0x00, "0x00 0x00"),
            (0x4D, 0x42, "MB (reversed)"),
            (0x42, 0x4C, "BL"),
            (0x42, 0x4E, "BN")
        ]
        
        for byte1, byte2, desc in common_headers:
            count = 0
            positions = []
            for i in range(len(all_data) - 1):
                if all_data[i] == byte1 and all_data[i+1] == byte2:
                    count += 1
                    positions.append(i)
            if count > 0:
                print(f"Found {desc} at positions: {positions}")

def check_sensor_communication(port, baud_rates=[9600, 2400, 4800, 19200]):
    """
    Test different baud rates to find correct communication settings
    """
    print("Testing different baud rates...")
    print("=" * 50)
    
    for baud in baud_rates:
        print(f"\nTesting baud rate: {baud}")
        try:
            ser = serial.Serial(port, baud, timeout=2)
            ser.reset_input_buffer()
            time.sleep(1)  # Wait for data
            
            if ser.in_waiting > 0:
                data = ser.read(min(20, ser.in_waiting))  # Read up to 20 bytes
                print(f"  Data received: {list(data)}")
                print(f"  Hex: {[f'0x{b:02X}' for b in data]}")
                
                # Check for BM header
                for i in range(len(data) - 1):
                    if data[i] == 0x42 and data[i+1] == 0x4D:
                        print(f"  ✓ Found 'BM' header at position {i}")
                        ser.close()
                        return baud
            else:
                print("  No data received")
                
            ser.close()
            
        except Exception as e:
            print(f"  Error: {e}")
    
    return None

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Debug ZH07 sensor header issues')
    parser.add_argument('--port', default='/dev/serial0', help='Serial port')
    parser.add_argument('--baud', type=int, default=9600, help='Baud rate')
    parser.add_argument('--readings', type=int, default=10, help='Number of readings to analyze')
    parser.add_argument('--test-baud', action='store_true', help='Test different baud rates')
    
    args = parser.parse_args()
    
    if args.test_baud:
        correct_baud = check_sensor_communication(args.port)
        if correct_baud:
            print(f"\n✓ Correct baud rate appears to be: {correct_baud}")
            args.baud = correct_baud
        else:
            print("\n✗ No valid communication found with tested baud rates")
            return
    
    try:
        print(f"Connecting to {args.port} at {args.baud} baud...")
        ser = serial.Serial(args.port, args.baud, timeout=1)
        ser.reset_input_buffer()
        
        print("Waiting for sensor to start sending data...")
        time.sleep(2)
        
        debug_zh07_header(ser, args.readings)
        
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check if sensor is connected properly")
        print("2. Verify the correct serial port")
        print("3. Try different baud rates (--test-baud)")
        print("4. Check sensor power supply")
        print("5. Verify sensor wiring (TX, RX, GND, VCC)")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == '__main__':
    main()
