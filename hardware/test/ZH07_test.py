import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from hardware.SensorInterface import SensorStatus, AirQualityLevel
from hardware.ParticulateMatter import ZH07

def create_valid_packet(pm25: int, pm10: int) -> bytes:
    # Format: BM, PM2.5 High, PM2.5 Low, PM10 High, PM10 Low, 0x00, 0x00, Checksum
    packet = bytearray()
    packet.extend(b'BM')
    packet.append((pm25 >> 8) & 0xFF)
    packet.append(pm25 & 0xFF)
    packet.append((pm10 >> 8) & 0xFF)
    packet.append(pm10 & 0xFF)
    packet.append(0x00)
    packet.append(0x00)
    checksum = sum(packet) % 256
    packet.append(checksum)
    return bytes(packet)

@patch('hardware.ParticulateMatter.serial.Serial')
def test_read_data_valid_packet(mock_serial_class):
    mock_serial = MagicMock()
    mock_serial.in_waiting = 9
    pm25_val = 35
    pm10_val = 50
    packet = create_valid_packet(pm25_val, pm10_val)
    mock_serial.read.return_value = packet
    mock_serial.is_open = True
    mock_serial_class.return_value = mock_serial

    sensor = ZH07(port="/dev/ttyUSB0")
    sensor.serial_conn = mock_serial
    sensor.status = SensorStatus.READY

    reading = sensor.read_data()

    assert reading is not None
    assert reading.data["pm2.5"] == pm25_val
    assert reading.data["pm10"] == pm10_val
    assert reading.status == SensorStatus.READY
    assert reading.quality_level == AirQualityLevel.GOOD
    assert isinstance(reading.timestamp, datetime)
    assert reading.raw_data == packet
