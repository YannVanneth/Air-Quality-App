import sqlite3
import logging
from sensor import SensorReading
from typing import Dict,List

class DataLogger:
    def __init__(self,db_path: str = "air_quality.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(f"{__name__}.DataLogger")
        self._init_database()
    def _init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    sensor_id TEXT NOT NULL,
                    sensor_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    status TEXT NOT NULL,
                    quality_level INTEGER NOT NULL,
                    raw_data TEXT
                )
            ''')
            conn.commit()
    def log_reading(self,reading: SensorReading):
        try:
          with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO readings 
                    (timestamp, sensor_id, sensor_type, data, status, quality_level, raw_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    reading.timestamp.isoformat(),
                    reading.sensor_id,
                    reading.sensor_type,
                    json.dumps(reading.data),
                    reading.status.value,
                    reading.quality_level.value,
                    reading.raw_data.hex() if reading.raw_data else None
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error logging reading: {e}")
    def get_recent_readings(self, limit : int = 100) -> List[Dict]:
        try:
            with sqlite3.connect(self,db_path) as conn:
                cursor = conn.execute('''
                    SELECT * FROM readings 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                
                columns = [description[0] for description in cursor.description]
                readings = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                # Parse JSON data
                for reading in readings:
                    reading['data'] = json.loads(reading['data'])
                
                return readings
        except Exception as e:
            self.logger.error(f"Error getting recent readings: {e}")
            return []


            

            