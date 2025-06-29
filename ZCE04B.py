import serial
import time
import sys

# Initialize serial port variable
ser = None

def init_serial_port(port='/dev/ttyS0', baudrate=9600, timeout=2):
    """Initialize serial port connection"""
    global ser
    try:
        ser = serial.Serial(port, baudrate, timeout=timeout)
        print(f"✓ Serial port opened successfully: {ser.port}")
        print(f"✓ Baudrate: {ser.baudrate}")
        print(f"✓ Timeout: {ser.timeout}")
        return True
    except serial.SerialException as e:
        print(f"✗ Failed to open serial port: {e}")
        return False

def calculate_crc16_modbus(data):
    """Calculate CRC16 for Modbus RTU protocol"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

def create_modbus_frame(slave_id, function_code, start_reg, num_regs):
    """Create a proper Modbus RTU frame"""
    frame = bytearray([
        slave_id,           # Slave address
        function_code,      # Function code
        (start_reg >> 8) & 0xFF,  # Start register high byte
        start_reg & 0xFF,   # Start register low byte
        (num_regs >> 8) & 0xFF,   # Number of registers high byte
        num_regs & 0xFF     # Number of registers low byte
    ])

    # Calculate CRC
    crc = calculate_crc16_modbus(frame)
    frame.append(crc & 0xFF)        # CRC low byte
    frame.append((crc >> 8) & 0xFF) # CRC high byte

    return frame

# Try different frame variations for ZCE04B
FRAME_VARIATIONS = [
    # Standard Modbus read holding registers
    create_modbus_frame(0x01, 0x03, 0x0000, 0x0004),  # Read 4 registers from 0x0000
    create_modbus_frame(0x01, 0x04, 0x0000, 0x0004),  # Read input registers from 0x0000
    create_modbus_frame(0xFF, 0x01, 0x86, 0x0001),     # Your original with fixes
    # Common ZCE04B variations
    create_modbus_frame(0x01, 0x03, 0x0086, 0x0001),  # Read 1 register from 0x86
    create_modbus_frame(0x01, 0x04, 0x0086, 0x0001),  # Read input register from 0x86
    # Broadcast variations
    bytearray([0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79]),  # Your original
    bytearray([0xFF, 0x86]),  # Simple command variant
]

def print_hex_bytes(data, label="Data"):
    """Helper function to print bytes in hex format"""
    hex_str = ' '.join([f'{b:02X}' for b in data])
    print(f"{label}: [{hex_str}] (Length: {len(data)})")

def test_frame_variation(frame, variation_name):
    """Test a specific frame variation"""
    print(f"\n🧪 Testing {variation_name}")
    print_hex_bytes(frame, "Request frame")

    # Clear buffer
    if ser.in_waiting > 0:
        old_data = ser.read(ser.in_waiting)
        print(f"⚠ Cleared {len(old_data)} bytes from buffer")

    try:
        # Send request
        bytes_written = ser.write(frame)
        print(f"✓ Wrote {bytes_written} bytes to serial port")
        ser.flush()
        print("✓ Serial buffer flushed")

        # Wait for response with multiple timeouts
        for wait_time in [0.1, 0.5, 1.0, 2.0]:
            time.sleep(wait_time)
            bytes_available = ser.in_waiting

            if bytes_available > 0:
                print(f"📊 Found {bytes_available} bytes after {wait_time}s wait")
                response = ser.read(bytes_available)
                print_hex_bytes(response, "Response")
                return response

            print(f"⏳ No response after {wait_time}s...")

        print("✗ No response received")
        return None

    except Exception as e:
        print(f"✗ Error during communication: {e}")
        return None

def scan_baudrates():
    """Try different baudrates"""
    global ser
    baudrates = [9600, 19200, 38400, 57600, 115200, 4800, 2400]

    for baud in baudrates:
        print(f"\n🔍 Testing baudrate: {baud}")
        try:
            if ser and ser.is_open:
                ser.close()

            test_ser = serial.Serial('/dev/ttyS0', baud, timeout=1)

            # Try simple frame
            test_frame = create_modbus_frame(0x01, 0x03, 0x0000, 0x0001)
            test_ser.write(test_frame)
            test_ser.flush()
            time.sleep(0.5)

            if test_ser.in_waiting > 0:
                response = test_ser.read(test_ser.in_waiting)
                print(f"🎯 RESPONSE FOUND at {baud} baud!")
                print_hex_bytes(response, "Response")
                test_ser.close()
                ser = serial.Serial('/dev/ttyS0', baud, timeout=2)  # Reinitialize with found baudrate
                return baud

            test_ser.close()

        except Exception as e:
            print(f"   Error at {baud}: {e}")

    return None

def get_gas_data():
    """Try all frame variations to get gas data"""
    print("\n" + "="*60)
    print("🔬 COMPREHENSIVE SENSOR TEST")
    print("="*60)

    # Test each frame variation
    for i, frame in enumerate(FRAME_VARIATIONS):
        variation_name = [
            "Standard Modbus Read Holding (0x03)",
            "Standard Modbus Read Input (0x04)",
            "Original Frame with CRC Fix",
            "ZCE04B Variant 1 (Holding Reg 0x86)",
            "ZCE04B Variant 2 (Input Reg 0x86)",
            "Original Frame (As-Is)",
            "Simple Command"
        ][i]

        response = test_frame_variation(frame, variation_name)

        if response and len(response) > 0:
            print(f"🎉 SUCCESS with {variation_name}!")
            return analyze_response(response)

        time.sleep(0.5)  # Brief pause between attempts

    return None

def analyze_response(response):
    """Analyze the sensor response"""
    print(f"\n📊 RESPONSE ANALYSIS")
    print(f"Length: {len(response)} bytes")

    if len(response) >= 4:
        print("Possible interpretations:")
        print(f"  Byte 0 (Address): 0x{response[0]:02X} ({response[0]})")
        print(f"  Byte 1 (Function): 0x{response[1]:02X} ({response[1]})")

        if len(response) >= 9:
            # Try to parse as gas data
            gas_data = {
                'Possible CO': response[2] if len(response) > 2 else 0,
                'Possible H2S': response[3] if len(response) > 3 else 0,
                'Possible CH4': response[4] if len(response) > 4 else 0,
                'Possible O2': response[5] if len(response) > 5 else 0
            }

            print("Potential gas readings:")
            for gas, value in gas_data.items():
                print(f"  {gas}: {value} (0x{value:02X})")

            return gas_data

    return {"raw_response": response.hex()}

def main():
    global ser
    print("🚀 ZCE04B Gas Sensor Advanced Diagnostic Tool")
    print("="*60)

    # Initialize serial port
    if not init_serial_port():
        print("❌ Cannot continue without serial port connection")
        sys.exit(1)

    try:
        print(f"Serial port: {ser.port}")

        # First, scan baudrates
        print("🔍 PHASE 1: Baudrate Detection")
        optimal_baud = scan_baudrates()

        if optimal_baud:
            print(f"\n🎯 Optimal baudrate found: {optimal_baud}")
        else:
            print("\n⚠ No response at any baudrate, continuing with 9600...")
            # Reinitialize with default
            if not init_serial_port():
                print("❌ Cannot reinitialize serial port")
                sys.exit(1)

        print("\n🔍 PHASE 2: Protocol Detection")

        iteration = 0
        successful_reads = 0

        while iteration < 5:  # Limit iterations for testing
            iteration += 1
            print(f"\n🔄 Iteration {iteration}")

            result = get_gas_data()

            if result:
                successful_reads += 1
                print("✅ SUCCESS: Got sensor response!")
                print(f"🎯 Result: {result}")

                if successful_reads >= 2:  # Stop after 2 successes
                    print("\n🎉 Sensor communication established!")
                    break
            else:
                print("❌ FAILED: No valid response")
                print("🔧 Hardware troubleshooting needed:")
                print("   1. Verify 12V/24V power to sensor")
                print("   2. Check RS485 A+/B- connections")
                print("   3. Ensure proper grounding")
                print("   4. Try different sensor address (DIP switches)")
                print("   5. Check if sensor needs initialization command")

            if iteration < 5:
                print(f"⏰ Waiting 3 seconds before next attempt...")
                time.sleep(3)

    except KeyboardInterrupt:
        print("\n🛑 Testing stopped by user")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("🔌 Serial port closed")

        print(f"\n📊 Final Statistics:")
        print(f"   Iterations: {iteration}")
        print(f"   Successful: {successful_reads}")
        print(f"   Success rate: {(successful_reads/iteration*100) if iteration > 0 else 0:.1f}%")

if __name__ == "__main__":
    main()
