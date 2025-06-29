
import serial
import time
import os
import stat
import glob

def find_serial_devices():
    """Find all available serial devices"""
    devices = []
    # Common serial device patterns
    patterns = ['/dev/ttyS*', '/dev/ttyAMA*', '/dev/ttyUSB*', '/dev/serial*']
    
    for pattern in patterns:
        devices.extend(glob.glob(pattern))
    
    return sorted(devices)

def check_device_permissions(device):
    """Check if device exists and permissions"""
    try:
        if not os.path.exists(device):
            return False, f"Device {device} does not exist"
            
        file_stat = os.stat(device)
        permissions = stat.filemode(file_stat.st_mode)
        readable = os.access(device, os.R_OK)
        writable = os.access(device, os.W_OK)
        
        return True, {
            'permissions': permissions,
            'readable': readable,
            'writable': writable,
            'owner': file_stat.st_uid,
            'group': file_stat.st_gid
        }
    except Exception as e:
        return False, str(e)

def test_serial_port(port, baudrate=9600):
    """Test if serial port can be opened"""
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        ser.close()
        return True, "Port opened successfully"
    except serial.SerialException as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

def debug_co2_sensor(port="/dev/ttyS0", baudrate=9600):
    """Enhanced CO2 sensor debugging"""
    print(f"\n--- Testing CO2 sensor on {port} at {baudrate} baud ---")
    
    try:
        # Test if port can be opened first
        success, message = test_serial_port(port, baudrate)
        if not success:
            print(f"❌ Cannot open port: {message}")
            return False
            
        # Open serial connection
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=2
        )
        
        print(f"✓ Serial port opened: {ser.port}")
        print(f"  Baudrate: {ser.baudrate}")
        print(f"  Timeout: {ser.timeout}s")
        
        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.1)
        
        # MH-Z19 command to read CO2 concentration
        cmd = bytearray([0xFF, 0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00, 0x79])
        print(f"📤 Sending command: {' '.join([f'{b:02X}' for b in cmd])}")
        
        # Send command
        bytes_written = ser.write(cmd)
        print(f"  Bytes written: {bytes_written}")
        
        # Wait for response
        time.sleep(0.5)
        
        # Check available bytes
        bytes_available = ser.in_waiting
        print(f"📥 Bytes available: {bytes_available}")
        
        if bytes_available == 0:
            print("❌ No response from sensor")
            # Try waiting longer
            print("  Waiting additional 2 seconds...")
            time.sleep(2)
            bytes_available = ser.in_waiting
            print(f"  Bytes available after wait: {bytes_available}")
        
        if bytes_available > 0:
            # Read all available bytes
            response = ser.read(bytes_available)
            print(f"📨 Raw response ({len(response)} bytes): {' '.join([f'{b:02X}' for b in response])}")
            
            # Parse if we got expected 9 bytes
            if len(response) >= 9:
                # Check if it's a valid MH-Z19 response
                if response[0] == 0xFF and response[1] == 0x86:
                    co2 = (response[2] << 8) | response[3]
                    print(f"✓ CO₂ concentration: {co2} ppm")
                    
                    # Verify checksum
                    checksum = 0xFF
                    for i in range(8):
                        checksum = (checksum - response[i]) & 0xFF
                    
                    print(f"  Calculated checksum: {checksum:02X}")
                    print(f"  Received checksum: {response[8]:02X}")
                    
                    if checksum == response[8]:
                        print("✓ Checksum valid")
                        return True
                    else:
                        print("❌ Checksum invalid")
                else:
                    print(f"❌ Invalid response header: {response[0]:02X} {response[1]:02X}")
            else:
                print(f"❌ Incomplete response ({len(response)} bytes, expected 9)")
        else:
            print("❌ No data received")
            
        ser.close()
        return False
        
    except serial.SerialException as e:
        print(f"❌ Serial error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_raspberry_pi_serial():
    """Check Raspberry Pi specific serial configuration"""
    print("\n--- Raspberry Pi Serial Configuration ---")
    
    # Check if running on Raspberry Pi
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
            if 'Raspberry Pi' not in cpuinfo:
                print("⚠️  Not running on Raspberry Pi")
                return
    except:
        print("⚠️  Cannot determine if running on Raspberry Pi")
        return
    
    # Check boot config
    config_files = ['/boot/config.txt', '/boot/firmware/config.txt']
    config_found = False
    
    for config_file in config_files:
        if os.path.exists(config_file):
            config_found = True
            print(f"📋 Checking {config_file}:")
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
                    
                    # Check relevant settings
                    settings = {
                        'enable_uart': 'enable_uart=1' in content,
                        'dtoverlay_disable_bt': 'dtoverlay=disable-bt' in content,
                        'core_freq': 'core_freq=' in content,
                        'dtoverlay_miniuart_bt': 'dtoverlay=miniuart-bt' in content
                    }
                    
                    for setting, found in settings.items():
                        status = "✓" if found else "❌"
                        print(f"  {status} {setting}: {'Found' if found else 'Not found'}")
                        
            except Exception as e:
                print(f"  ❌ Error reading config: {e}")
            break
    
    if not config_found:
        print("❌ Boot config file not found")
    
    # Check if serial console is disabled
    try:
        with open('/proc/cmdline', 'r') as f:
            cmdline = f.read().strip()
            if 'console=serial0' in cmdline or 'console=ttyAMA0' in cmdline:
                print("⚠️  Serial console is enabled - this may interfere with sensor")
                print("   Disable with: sudo raspi-config > Advanced Options > Serial > No")
            else:
                print("✓ Serial console appears to be disabled")
    except:
        print("❌ Cannot check serial console status")

def main():
    print("=" * 50)
    print("🔧 Enhanced CO2 Sensor Debug Tool")
    print("=" * 50)
    
    # Find available serial devices
    print("\n1️⃣ Finding serial devices...")
    devices = find_serial_devices()
    
    if not devices:
        print("❌ No serial devices found")
        return
    
    print(f"✓ Found {len(devices)} serial device(s):")
    for device in devices:
        exists, info = check_device_permissions(device)
        if exists:
            print(f"  📍 {device}")
            print(f"    Permissions: {info['permissions']}")
            print(f"    Readable: {'✓' if info['readable'] else '❌'}")
            print(f"    Writable: {'✓' if info['writable'] else '❌'}")
        else:
            print(f"  ❌ {device}: {info}")
    
    # Check Raspberry Pi specific settings
    check_raspberry_pi_serial()
    
    # Test CO2 sensor on available devices
    print("\n2️⃣ Testing CO2 sensor communication...")
    
    # Primary devices to test
    test_devices = ["/dev/serial0", "/dev/ttyS0", "/dev/ttyAMA0"]
    baudrates = [9600, 19200, 38400]  # Common baudrates for MH-Z19
    
    success = False
    for device in test_devices:
        if device in devices:
            for baudrate in baudrates:
                if debug_co2_sensor(device, baudrate):
                    success = True
                    break
            if success:
                break
    
    if not success:
        print("\n❌ CO2 sensor communication failed on all tested configurations")
        print("\n🔧 Troubleshooting suggestions:")
        print("1. Check power supply (5V DC, stable)")
        print("2. Verify wiring connections:")
        print("   - Sensor TX → Pi GPIO 15 (Pin 10)")
        print("   - Sensor RX → Pi GPIO 14 (Pin 8)")
        print("   - Sensor GND → Pi GND")
        print("   - Sensor VCC → Pi 5V")
        print("3. Enable UART: sudo raspi-config → Interface Options → Serial Port")
        print("   - Enable serial interface: Yes")
        print("   - Disable serial console: No")
        print("4. Add to /boot/config.txt:")
        print("   enable_uart=1")
        print("   dtoverlay=disable-bt")
        print("5. Reboot after configuration changes")
        print("6. Check sensor warm-up time (3+ minutes)")
        print("7. Try different sensor (hardware may be faulty)")
    else:
        print("\n✅ CO2 sensor communication successful!")

if __name__ == "__main__":
    main()
