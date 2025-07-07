#!/usr/bin/env python3
"""
ZE08-CH2O Formaldehyde Sensor - Correct Implementation
Based on Official Winsen ZE08-CH2O Documentation v1.7

Hardware Connection:
- Pin 1: Reserved (no connection)
- Pin 2: DAC (0.4~2V analog output) - optional
- Pin 3: GND → Raspberry Pi GND
- Pin 4: Vin (3.7V~5.5V) → Raspberry Pi 5V or 3.3V
- Pin 5: UART RXD → Raspberry Pi TX (GPIO 14)
- Pin 6: UART TXD → Raspberry Pi RX (GPIO 15)
- Pin 7: Reserved (no connection)

Communication Modes:
1. Active Upload Mode (default): Sensor sends data every second
2. Q&A Mode: Request/response communication

Author: Based on working implementation
"""

import serial
import time
import sys

class ZE08_CH2O:
    def __init__(self, port='/dev/ttyUSB0', baudrate=9600):
        """
        Initialize ZE08-CH2O formaldehyde sensor
        
        Args:
            port: Serial port (default: /dev/ttyUSB0)
            baudrate: Communication speed (9600 as per datasheet)
        """
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.is_active_mode = True
        
    def connect(self):
        """Establish serial connection to sensor"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=8,
                parity=serial.PARITY_NONE,
                stopbits=1,
                timeout=2
            )
            print(f"✓ Connected to ZE08-CH2O on {self.port}")
            print("⏱ Sensor warming up (3 minutes required for stable readings)...")
            time.sleep(1)
            return True
            
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            print("Check:")
            print("  - Sensor is powered")
            print("  - Serial port is correct")
            print("  - Wiring connections")
            return False
    
    def disconnect(self):
        """Close serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("✓ Serial connection closed")
    
    def calculate_checksum(self, data):
        """
        Calculate checksum according to datasheet
        Formula: ~(Byte1 + Byte2 + ... + Byte7) + 1
        
        Args:
            data: List of bytes (excluding start byte 0xFF)
            
        Returns:
            int: Calculated checksum byte
        """
        checksum = sum(data) & 0xFF
        return ((~checksum) + 1) & 0xFF
    
    def switch_to_active_mode(self):
        """
        Switch sensor to active upload mode (sends data every second)
        Command: 0xFF 0x01 0x78 0x40 0x00 0x00 0x00 0x00 0x47
        """
        if not self.ser or not self.ser.is_open:
            print("✗ Sensor not connected")
            return False
        
        try:
            # Build command without checksum
            command = [0x01, 0x78, 0x40, 0x00, 0x00, 0x00, 0x00]
            checksum = self.calculate_checksum(command)
            
            # Complete command with start byte and checksum
            full_command = bytearray([0xFF] + command + [checksum])
            
            self.ser.write(full_command)
            time.sleep(0.5)
            
            # Clear any pending data
            self.ser.reset_input_buffer()
            
            self.is_active_mode = True
            print("✓ Switched to Active Upload mode")
            return True
            
        except Exception as e:
            print(f"✗ Error switching to active mode: {e}")
            return False
    
    def switch_to_qa_mode(self):
        """
        Switch sensor to Q&A mode (request/response)
        Command: 0xFF 0x01 0x78 0x41 0x00 0x00 0x00 0x00 0x46
        """
        if not self.ser or not self.ser.is_open:
            print("✗ Sensor not connected")
            return False
        
        try:
            # Build command without checksum
            command = [0x01, 0x78, 0x41, 0x00, 0x00, 0x00, 0x00]
            checksum = self.calculate_checksum(command)
            
            # Complete command with start byte and checksum
            full_command = bytearray([0xFF] + command + [checksum])
            
            self.ser.write(full_command)
            time.sleep(0.5)
            
            # Clear any pending data
            self.ser.reset_input_buffer()
            
            self.is_active_mode = False
            print("✓ Switched to Q&A mode")
            return True
            
        except Exception as e:
            print(f"✗ Error switching to Q&A mode: {e}")
            return False
    
    def read_concentration_qa(self):
        """
        Read concentration in Q&A mode
        Send command: 0xFF 0x01 0x86 0x00 0x00 0x00 0x00 0x00 0x79
        Response: 0xFF 0x86 [ug_high] [ug_low] 0x00 0x00 [ppb_high] [ppb_low] [checksum]
        
        Returns:
            dict: {'ppb': int, 'ppm': float, 'mg_m3': float, 'ug_m3': int} or None
        """
        if not self.ser or not self.ser.is_open:
            print("✗ Sensor not connected")
            return None
        
        try:
            # Build read command
            command = [0x01, 0x86, 0x00, 0x00, 0x00, 0x00, 0x00]
            checksum = self.calculate_checksum(command)
            full_command = bytearray([0xFF] + command + [checksum])
            
            # Send command and wait for response
            self.ser.write(full_command)
            time.sleep(0.2)
            
            # Read 9-byte response
            if self.ser.in_waiting >= 9:
                response = self.ser.read(9)
                
                if len(response) == 9 and response[0] == 0xFF and response[1] == 0x86:
                    # Parse response
                    ug_m3 = (response[2] << 8) | response[3]  # µg/m³
                    ppb = (response[6] << 8) | response[7]    # ppb
                    
                    # Convert to other units
                    ppm = ppb / 1000.0
                    mg_m3 = ppm * 1.25  # As per datasheet: 1PPM × 1.25 = 1.25mg/m³
                    
                    return {
                        'ppb': ppb,
                        'ppm': ppm,
                        'mg_m3': mg_m3,
                        'ug_m3': ug_m3
                    }
                else:
                    print("✗ Invalid response format")
                    return None
            else:
                print("✗ No response from sensor")
                return None
                
        except Exception as e:
            print(f"✗ Error reading Q&A mode: {e}")
            return None
    
    def read_concentration_active(self):
        """
        Read concentration in active upload mode
        Expected response: 0xFF 0x17 0x04 0x00 [conc_high] [conc_low] [range_high] [range_low] [checksum]
        
        Returns:
            dict: {'ppb': int, 'ppm': float, 'mg_m3': float} or None
        """
        if not self.ser or not self.ser.is_open:
            print("✗ Sensor not connected")
            return None
        
        try:
            # Clear input buffer to get fresh data
            self.ser.reset_input_buffer()
            
            # Wait for data (sensor sends every second)
            start_time = time.time()
            while time.time() - start_time < 3:
                if self.ser.in_waiting >= 9:
                    response = self.ser.read(9)
                    
                    if (len(response) == 9 and 
                        response[0] == 0xFF and 
                        response[1] == 0x17 and 
                        response[2] == 0x04):  # 0x04 = ppb unit
                        
                        # Extract concentration from bytes 4-5
                        ppb = (response[4] << 8) | response[5]
                        
                        # Convert to other units
                        ppm = ppb / 1000.0
                        mg_m3 = ppm * 1.25  # As per datasheet
                        
                        return {
                            'ppb': ppb,
                            'ppm': ppm,
                            'mg_m3': mg_m3
                        }
                
                time.sleep(0.1)
            
            print("✗ No valid data received in active mode")
            return None
            
        except Exception as e:
            print(f"✗ Error reading active mode: {e}")
            return None
    
    def read_concentration(self):
        """
        Read concentration (automatically detects mode)
        
        Returns:
            dict: Concentration data or None if error
        """
        if self.is_active_mode:
            return self.read_concentration_active()
        else:
            return self.read_concentration_qa()
    
    def get_air_quality_level(self, mg_m3):
        """
        Determine air quality level based on formaldehyde concentration
        
        Args:
            mg_m3: Concentration in mg/m³
            
        Returns:
            tuple: (level, description, emoji)
        """
        if mg_m3 < 0.08:
            return ("Excellent", "Safe level", "🟢")
        elif mg_m3 < 0.10:
            return ("Good", "Acceptable", "🟡")
        elif mg_m3 < 0.12:
            return ("Moderate", "Caution advised", "🟠")
        elif mg_m3 < 0.16:
            return ("Poor", "Health risk", "🔴")
        else:
            return ("Hazardous", "Dangerous level", "🚨")
    
    def read_multiple(self, count=5, delay=5):
        """
        Take multiple readings for averaging
        
        Args:
            count: Number of readings to take
            delay: Delay between readings in seconds
            
        Returns:
            list: List of successful readings
        """
        readings = []
        print(f"Taking {count} readings...")
        
        for i in range(count):
            print(f"Reading {i+1}/{count}...", end=" ")
            
            data = self.read_concentration()
            if data:
                readings.append(data)
                print(f"✓ {data['ppm']:.3f} ppm")
            else:
                print("✗ Failed")
            
            if i < count - 1:  # Don't delay after last reading
                time.sleep(delay)
        
        return readings
    
    def get_average(self, count=5):
        """
        Get average concentration from multiple readings
        
        Args:
            count: Number of readings to average
            
        Returns:
            dict: Average values or None if no readings
        """
        readings = self.read_multiple(count)
        
        if not readings:
            print("✗ No successful readings for averaging")
            return None
        
        # Calculate averages
        avg_ppb = sum(r['ppb'] for r in readings) / len(readings)
        avg_ppm = sum(r['ppm'] for r in readings) / len(readings)
        avg_mg_m3 = sum(r['mg_m3'] for r in readings) / len(readings)
        
        print(f"📊 Average from {len(readings)} readings:")
        
        return {
            'ppb': avg_ppb,
            'ppm': avg_ppm,
            'mg_m3': avg_mg_m3
        }
    
    def monitor_continuous(self, duration=60):
        """
        Monitor continuously for specified duration
        
        Args:
            duration: Monitoring duration in seconds
        """
        print(f"🔄 Starting continuous monitoring for {duration} seconds")
        print("Press Ctrl+C to stop early\n")
        
        start_time = time.time()
        reading_count = 0
        
        try:
            while (time.time() - start_time) < duration:
                data = self.read_concentration()
                
                if data:
                    reading_count += 1
                    timestamp = time.strftime("%H:%M:%S")
                    level, desc, emoji = self.get_air_quality_level(data['mg_m3'])
                    
                    print(f"[{timestamp}] {emoji} CH2O: {data['ppm']:.3f} ppm "
                          f"({data['ppb']} ppb, {data['mg_m3']:.3f} mg/m³) - {level}")
                else:
                    print(f"[{time.strftime('%H:%M:%S')}] ✗ Reading failed")
                
                time.sleep(1 if self.is_active_mode else 3)
                
        except KeyboardInterrupt:
            print(f"\n⏹ Monitoring stopped (took {reading_count} readings)")

def main():
    """Main test function with interactive menu"""
    print("🌡️  ZE08-CH2O Formaldehyde Sensor")
    print("📋 Based on Official Winsen Documentation v1.7")
    print("=" * 50)
    
    # Initialize sensor
    sensor = ZE08_CH2O(port='/dev/ttyUSB0')
    
    if not sensor.connect():
        print("❌ Failed to connect to sensor")
        print("Common solutions:")
        print("  • Check if sensor is powered")
        print("  • Try different port: /dev/ttyUSB0, /dev/ttyS0, /dev/ttyAMA0")
        print("  • Check wiring connections")
        return
    
    try:
        while True:
            print("\n📋 Select operation:")
            print("1. 🔄 Active Mode (auto-upload every second)")
            print("2. 🤝 Q&A Mode (request/response)")
            print("3. 📊 Multiple readings with average")
            print("4. ⏱️  Continuous monitoring")
            print("5. 🔧 Switch communication mode")
            print("6. ❌ Exit")
            
            choice = input("\nEnter choice (1-6): ").strip()
            
            if choice == "1":
                print("\n🔄 Active Upload Mode")
                sensor.switch_to_active_mode()
                print("Sensor sends data automatically every second")
                print("Press Ctrl+C to stop\n")
                
                try:
                    while True:
                        data = sensor.read_concentration()
                        if data:
                            level, desc, emoji = sensor.get_air_quality_level(data['mg_m3'])
                            print(f"{emoji} CH2O: {data['ppm']:.3f} ppm "
                                  f"({data['ppb']} ppb, {data['mg_m3']:.3f} mg/m³)")
                            print(f"   Air Quality: {level} - {desc}")
                        else:
                            print("✗ Failed to read data")
                        
                        print("-" * 40)
                        time.sleep(1)
                        
                except KeyboardInterrupt:
                    print("\n⏹ Stopped active mode reading")
            
            elif choice == "2":
                print("\n🤝 Q&A Mode")
                sensor.switch_to_qa_mode()
                print("Manual request/response mode")
                print("Press Ctrl+C to stop\n")
                
                try:
                    while True:
                        input("Press Enter to take reading...")
                        data = sensor.read_concentration()
                        
                        if data:
                            level, desc, emoji = sensor.get_air_quality_level(data['mg_m3'])
                            print(f"{emoji} CH2O Concentration:")
                            print(f"   {data['ppb']:.0f} ppb")
                            print(f"   {data['ppm']:.3f} ppm")
                            print(f"   {data['mg_m3']:.3f} mg/m³")
                            if 'ug_m3' in data:
                                print(f"   {data['ug_m3']:.0f} µg/m³")
                            print(f"   Air Quality: {level} - {desc}")
                        else:
                            print("✗ Failed to read data")
                        
                        print("-" * 40)
                        
                except KeyboardInterrupt:
                    print("\n⏹ Stopped Q&A mode reading")
            
            elif choice == "3":
                print("\n📊 Multiple Readings with Average")
                try:
                    count = int(input("Number of readings (default=5): ") or "5")
                    avg_data = sensor.get_average(count)
                    
                    if avg_data:
                        level, desc, emoji = sensor.get_air_quality_level(avg_data['mg_m3'])
                        print(f"\n{emoji} Average Results:")
                        print(f"   {avg_data['ppb']:.1f} ppb")
                        print(f"   {avg_data['ppm']:.3f} ppm")
                        print(f"   {avg_data['mg_m3']:.3f} mg/m³")
                        print(f"   Overall Air Quality: {level} - {desc}")
                        
                except ValueError:
                    print("✗ Invalid number entered")
            
            elif choice == "4":
                print("\n⏱️  Continuous Monitoring")
                try:
                    duration = int(input("Duration in seconds (default=60): ") or "60")
                    sensor.monitor_continuous(duration)
                except ValueError:
                    print("✗ Invalid duration entered")
            
            elif choice == "5":
                print("\n🔧 Communication Mode")
                print("1. Switch to Active Mode")
                print("2. Switch to Q&A Mode")
                mode_choice = input("Enter choice (1-2): ").strip()
                
                if mode_choice == "1":
                    sensor.switch_to_active_mode()
                elif mode_choice == "2":
                    sensor.switch_to_qa_mode()
                else:
                    print("✗ Invalid choice")
            
            elif choice == "6":
                print("\n👋 Goodbye!")
                break
            
            else:
                print("✗ Invalid choice. Please select 1-6.")
    
    except KeyboardInterrupt:
        print("\n\n⏹ Program interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        sensor.disconnect()

if __name__ == "__main__":
    main()
