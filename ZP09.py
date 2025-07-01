import time
import threading
from enum import Enum
from typing import Optional, Callable, Dict, Any, Tuple
import logging

class ModuleState(Enum):
    """Module operational states"""
    INITIALIZING = "initializing"
    WARMING_UP = "warming_up"
    READY = "ready"
    READING = "reading"
    FAULT = "fault"
    SLEEP = "sleep"

class PollutionLevel(Enum):
    """Air pollution levels (0-10 grade)"""
    EXCELLENT = 0
    VERY_GOOD = 1
    GOOD = 2
    LIGHT = 3
    MODERATE = 4
    MEDIUM = 5
    HEAVY = 6
    VERY_HEAVY = 7
    SEVERE = 8
    EXTREMELY_SEVERE = 9
    HAZARDOUS = 10

class ZP07_MP503:
    """
    Python interface for ZP07-MP503 Air Quality Detection Module
    
    Official Specifications:
    - Detection: formaldehyde, benzene, CO, hydrogen, alcohol, ammonia, cigarette smoke, etc.
    - Output: 0-10 grade pollution signal (TTL level)
    - Working Voltage: 5.0±0.2V DC (≤60mA)
    - Warm-up Time: ≤3 min, Response Time: ≤20s, Recovery Time: ≤60s
    - Operating: 0~50℃, ≤95%RH
    - Life Span: ≥5 years, Sensitivity Attenuator: ≤1%/year
    - Physical Interface: XH2.54-4P terminal sockets
    """
    
    # PWM signal mapping for pollution levels (High ms, Low ms)
    PWM_SIGNAL_MAP = {
        0: (0, 100),    # Pollution Class 0
        1: (10, 90),    # Pollution Class 1
        2: (20, 80),    # Pollution Class 2
        3: (30, 70),    # Pollution Class 3
        4: (40, 60),    # Pollution Class 4
        5: (50, 50),    # Pollution Class 5
        6: (60, 40),    # Pollution Class 6
        7: (70, 30),    # Pollution Class 7
        8: (80, 20),    # Pollution Class 8
        9: (90, 10),    # Pollution Class 9
        10: (100, 0)    # Pollution Class 10
    }
    
    def __init__(self, 
                 warm_up_time: int = 180,  # Default 3 minutes as per spec
                 response_time: int = 20,   # Response time ≤20s
                 recovery_time: int = 60,   # Recovery time ≤60s
                 enable_auto_check: bool = True):
        """
        Initialize the ZP07-MP503 module
        
        Args:
            warm_up_time: Warm-up duration in seconds (≤3 min per spec)
            response_time: Sensor response time in seconds (≤20s per spec)
            recovery_time: Sensor recovery time in seconds (≤60s per spec)
            enable_auto_check: Enable automatic fault checking
        """
        # Module specifications
        self.warm_up_time = min(warm_up_time, 180)  # Max 3 minutes
        self.response_time = min(response_time, 20)  # Max 20 seconds
        self.recovery_time = min(recovery_time, 60)  # Max 60 seconds
        self.enable_auto_check = enable_auto_check
        
        # Power specifications
        self.working_voltage = 5.0  # 5.0±0.2V DC
        self.working_current = 60   # ≤60mA
        self.max_voltage = 5.5      # Damage threshold
        
        # Environmental specifications
        self.operating_temp_range = (0, 50)    # 0~50℃
        self.operating_humidity_max = 95       # ≤95%RH
        self.storage_temp_range = (-20, 60)    # -20~60℃
        self.storage_humidity_max = 60         # ≤60%RH
        
        # Module state
        self.state = ModuleState.INITIALIZING
        self.current_pollution_level = 0
        self.is_warmed_up = False
        self.last_reading_time = None
        self.start_time = time.time()
        
        # Sensor data
        self.detected_gases = {
            'formaldehyde': 0.0,
            'benzene': 0.0,
            'carbon_monoxide': 0.0,
            'hydrogen': 0.0,
            'alcohol': 0.0,
            'ammonia': 0.0,
            'cigarette_smoke': 0.0,
            'organic_compounds': 0.0
        }
        
        # Environmental monitoring
        self.temperature = 25.0
        self.humidity = 50.0
        self.voltage = 5.0
        self.current = 45.0
        
        # Threading for background operations
        self.monitoring_thread = None
        self.monitoring_active = False
        
        # Callbacks
        self.fault_callback: Optional[Callable] = None
        self.level_change_callback: Optional[Callable] = None
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Start initialization
        self._initialize()
    
    def _initialize(self):
        """Initialize the module with automatic warm-up"""
        self.logger.info("Initializing ZP07-MP503 Air Quality Detection Module...")
        self.logger.info("Please warm up for 5 min before first using (as per manual)")
        
        # Voltage check
        if self.voltage > self.max_voltage:
            self.logger.error(f"Voltage {self.voltage}V exceeds maximum {self.max_voltage}V - module may be damaged!")
            self.state = ModuleState.FAULT
            return
        
        self.state = ModuleState.WARMING_UP
        
        # Start warm-up sequence
        warm_up_thread = threading.Thread(target=self._warm_up_sequence)
        warm_up_thread.daemon = True
        warm_up_thread.start()
        
        # Start monitoring if auto-check enabled
        if self.enable_auto_check:
            self._start_monitoring()
    
    def _warm_up_sequence(self):
        """Automatic warm-up function (≤3 minutes)"""
        self.logger.info(f"Starting warm-up sequence ({self.warm_up_time}s)...")
        
        # Simulate gradual warm-up with status updates
        steps = 10
        step_time = self.warm_up_time / steps
        
        for step in range(steps):
            if self.state == ModuleState.FAULT:
                return
            
            time.sleep(step_time)
            progress = (step + 1) / steps * 100
            self.logger.debug(f"Warm-up progress: {progress:.1f}%")
        
        # Warm-up complete
        self.is_warmed_up = True
        self.state = ModuleState.READY
        self.logger.info("Warm-up completed - Module ready for detection")
    
    def _start_monitoring(self):
        """Start automatic fault checking and monitoring"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
            self.monitoring_thread.daemon = True
            self.monitoring_thread.start()
    
    def _monitoring_loop(self):
        """Background monitoring for faults and environmental conditions"""
        while self.monitoring_active:
            self._perform_fault_check()
            time.sleep(5)  # Check every 5 seconds
    
    def _perform_fault_check(self):
        """Automatic fault detection"""
        fault_detected = False
        
        # Temperature range check
        if not (self.operating_temp_range[0] <= self.temperature <= self.operating_temp_range[1]):
            self.logger.warning(f"Temperature {self.temperature}°C outside operating range {self.operating_temp_range}")
            fault_detected = True
        
        # Humidity check
        if self.humidity > self.operating_humidity_max:
            self.logger.warning(f"Humidity {self.humidity}% exceeds maximum {self.operating_humidity_max}%")
            fault_detected = True
        
        # Voltage check
        if self.voltage > self.max_voltage:
            self.logger.error(f"Voltage {self.voltage}V exceeds safe maximum {self.max_voltage}V!")
            fault_detected = True
        elif not (4.8 <= self.voltage <= 5.2):  # 5.0±0.2V
            self.logger.warning(f"Voltage {self.voltage}V outside specification (5.0±0.2V)")
        
        # Current check
        if self.current > self.working_current:
            self.logger.warning(f"Current {self.current}mA exceeds specification ({self.working_current}mA)")
            fault_detected = True
        
        if fault_detected and self.state != ModuleState.FAULT:
            self.state = ModuleState.FAULT
            if self.fault_callback:
                self.fault_callback("Environmental conditions outside specifications")
        elif not fault_detected and self.state == ModuleState.FAULT:
            self.state = ModuleState.READY if self.is_warmed_up else ModuleState.WARMING_UP
            self.logger.info("Fault conditions cleared")
    
    def read_pollution_level(self) -> Dict[str, Any]:
        """
        Read air quality pollution level (0-10 grade)
        
        Returns:
            Dictionary containing pollution level and PWM signal data
        """
        if not self.is_warmed_up:
            raise RuntimeError("Module not warmed up yet. Please wait for warm-up completion.")
        
        if self.state == ModuleState.FAULT:
            raise RuntimeError("Module in fault state. Check environmental conditions.")
        
        self.state = ModuleState.READING
        
        # Simulate sensor reading with response time
        start_time = time.time()
        
        # Simulate detection of various gases (values would come from actual sensor)
        import random
        
        # Generate pollution level (0-10 grade)
        self.current_pollution_level = random.randint(0, 10)
        
        # Get PWM signal characteristics
        high_ms, low_ms = self.PWM_SIGNAL_MAP[self.current_pollution_level]
        
        # Simulate gas concentrations based on pollution level
        base_concentration = self.current_pollution_level * 10
        self.detected_gases = {
            'formaldehyde': base_concentration + random.uniform(-5, 5),
            'benzene': base_concentration * 0.8 + random.uniform(-3, 3),
            'carbon_monoxide': base_concentration * 1.2 + random.uniform(-8, 8),
            'hydrogen': base_concentration * 0.6 + random.uniform(-2, 2),
            'alcohol': base_concentration * 0.9 + random.uniform(-4, 4),
            'ammonia': base_concentration * 0.7 + random.uniform(-3, 3),
            'cigarette_smoke': base_concentration * 1.1 + random.uniform(-6, 6),
            'organic_compounds': base_concentration + random.uniform(-7, 7)
        }
        
        # Ensure non-negative values
        for gas in self.detected_gases:
            self.detected_gases[gas] = max(0, self.detected_gases[gas])
        
        # Wait for response time
        elapsed = time.time() - start_time
        if elapsed < self.response_time:
            time.sleep(self.response_time - elapsed)
        
        reading_data = {
            'timestamp': time.time(),
            'pollution_level': self.current_pollution_level,
            'pollution_class': PollutionLevel(self.current_pollution_level).name,
            'pwm_signal': {
                'high_ms': high_ms,
                'low_ms': low_ms,
                'duty_cycle_percent': high_ms
            },
            'detected_gases': self.detected_gases.copy(),
            'environmental': {
                'temperature_c': self.temperature,
                'humidity_percent': self.humidity,
                'voltage_v': self.voltage,
                'current_ma': self.current
            },
            'response_time_s': self.response_time
        }
        
        self.last_reading_time = reading_data['timestamp']
        self.state = ModuleState.READY
        
        # Callback for level changes
        if self.level_change_callback:
            self.level_change_callback(self.current_pollution_level)
        
        return reading_data
    
    def get_pwm_signal(self) -> Tuple[int, int]:
        """
        Get current PWM signal characteristics
        
        Returns:
            Tuple of (high_ms, low_ms) for TTL output
        """
        return self.PWM_SIGNAL_MAP.get(self.current_pollution_level, (0, 100))
    
    def set_environmental_conditions(self, temperature: float, humidity: float, voltage: float = None):
        """
        Update environmental conditions for monitoring
        
        Args:
            temperature: Temperature in Celsius (0~50℃ operating range)
            humidity: Relative humidity percentage (≤95%RH)
            voltage: Supply voltage (5.0±0.2V DC)
        """
        self.temperature = temperature
        self.humidity = humidity
        if voltage is not None:
            self.voltage = voltage
    
    def set_fault_callback(self, callback: Callable[[str], None]):
        """Set callback function for fault notifications"""
        self.fault_callback = callback
    
    def set_level_change_callback(self, callback: Callable[[int], None]):
        """Set callback function for pollution level changes"""
        self.level_change_callback = callback
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive module status"""
        uptime = time.time() - self.start_time
        
        return {
            'model': 'ZP07-MP503',
            'state': self.state.value,
            'is_warmed_up': self.is_warmed_up,
            'current_pollution_level': self.current_pollution_level,
            'pollution_class': PollutionLevel(self.current_pollution_level).name,
            'uptime_seconds': round(uptime, 2),
            'last_reading_time': self.last_reading_time,
            'specifications': {
                'working_voltage_v': f"{self.working_voltage}±0.2",
                'working_current_ma': f"≤{self.working_current}",
                'warm_up_time_s': f"≤{self.warm_up_time}",
                'response_time_s': f"≤{self.response_time}",
                'recovery_time_s': f"≤{self.recovery_time}",
                'operating_temp_c': f"{self.operating_temp_range[0]}~{self.operating_temp_range[1]}",
                'operating_humidity_rh': f"≤{self.operating_humidity_max}%",
                'life_span_years': "≥5",
                'sensitivity_attenuator': "≤1%/year"
            },
            'environmental': {
                'temperature_c': self.temperature,
                'humidity_percent': self.humidity,
                'voltage_v': self.voltage,
                'current_ma': self.current
            },
            'detected_gases': list(self.detected_gases.keys())
        }
    
    def get_sensitivity_info(self) -> Dict[str, str]:
        """Get information about gas sensitivity"""
        return {
            'detection_gases': [
                'formaldehyde', 'benzene', 'carbon monoxide', 
                'hydrogen', 'alcohol', 'ammonia', 
                'cigarette smoke', 'essence and other organic compounds'
            ],
            'sensitivity_note': 'Good sensitivity to volatile organic gases',
            'consistency': 'Good consistency and high sensitivity after aging, debugging, adjustment and calibration',
            'calibration': 'Calibrated before shipment'
        }
    
    def shutdown(self):
        """Gracefully shutdown the module"""
        self.logger.info("Shutting down ZP07-MP503 module...")
        self.monitoring_active = False
        self.state = ModuleState.SLEEP
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=2)


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    def on_fault_detected(fault_message):
        print(f"⚠️  Fault detected: {fault_message}")
    
    def on_level_change(pollution_level):
        level_name = PollutionLevel(pollution_level).name
        print(f"🌬️  Pollution level changed: {pollution_level} ({level_name})")
    
    # Initialize module with official specifications
    sensor = ZP07_MP503(
        warm_up_time=30,        # Quick demo (normally 3 minutes)
        response_time=20,       # ≤20s as per spec
        recovery_time=60,       # ≤60s as per spec
        enable_auto_check=True
    )
    
    # Set callbacks
    sensor.set_fault_callback(on_fault_detected)
    sensor.set_level_change_callback(on_level_change)
    
    print("🔄 ZP07-MP503 Air Quality Detection Module initializing...")
    print("📋 Module Specifications:")
    status = sensor.get_status()
    specs = status['specifications']
    for key, value in specs.items():
        print(f"   {key.replace('_', ' ').title()}: {value}")
    
    # Wait for module to be ready
    while sensor.state != ModuleState.READY:
        status = sensor.get_status()
        print(f"Status: {status['state']} (uptime: {status['uptime_seconds']:.1f}s)")
        time.sleep(2)
        
        if sensor.state == ModuleState.FAULT:
            print("❌ Module fault detected!")
            break
    
    # Take readings if module is ready
    if sensor.state == ModuleState.READY:
        print(f"\n🧪 Detecting gases: {', '.join(sensor.get_sensitivity_info()['detection_gases'])}")
        print("📊 Taking air quality measurements...")
        
        # Simulate different environmental conditions
        test_conditions = [
            (25, 45, 5.0),  # Normal conditions
            (35, 70, 4.9),  # Warmer, more humid
            (15, 30, 5.1),  # Cooler, dry
        ]
        
        for i, (temp, humidity, voltage) in enumerate(test_conditions):
            sensor.set_environmental_conditions(temp, humidity, voltage)
            
            try:
                reading = sensor.read_pollution_level()
                pwm_high, pwm_low = sensor.get_pwm_signal()
                
                print(f"\n📈 Reading {i+1} (Temp: {temp}°C, RH: {humidity}%, V: {voltage}V):")
                print(f"  Pollution Level: {reading['pollution_level']}/10 ({reading['pollution_class']})")
                print(f"  PWM Signal: {pwm_high}ms high, {pwm_low}ms low ({reading['pwm_signal']['duty_cycle_percent']}% duty)")
                print(f"  Response Time: {reading['response_time_s']}s")
                
                print("  🧪 Detected Gas Levels:")
                for gas, level in reading['detected_gases'].items():
                    if level > 0:
                        print(f"     {gas.replace('_', ' ').title()}: {level:.1f}")
                
                time.sleep(2)
                
            except RuntimeError as e:
                print(f"❌ Error taking reading: {e}")
                break
    
    # Display final status and sensitivity info
    final_status = sensor.get_status()
    print(f"\n📋 Final Status:")
    print(f"   Model: {final_status['model']}")
    print(f"   State: {final_status['state']}")
    print(f"   Uptime: {final_status['uptime_seconds']:.1f}s")
    print(f"   Current Pollution Level: {final_status['current_pollution_level']}/10")
    
    sensitivity_info = sensor.get_sensitivity_info()
    print(f"\n🔬 Sensitivity Information:")
    print(f"   {sensitivity_info['sensitivity_note']}")
    print(f"   {sensitivity_info['consistency']}")
    print(f"   {sensitivity_info['calibration']}")
    
    # Shutdown
    sensor.shutdown()
    print("🔌 Module shutdown complete")
    
    print("\n⚠️  Important Safety Notes (from manual):")
    print("   • Do not exceed 5.5V supply voltage (irreversible damage)")
    print("   • Warm up for 5 min before first use")
    print("   • Avoid organic solvents, high concentration gases")
    print("   • Do not use for personal safety applications")
    print("   • Operating range: 0~50℃, ≤95%RH")



