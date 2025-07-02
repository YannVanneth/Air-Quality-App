
import logging
from datetime import datetime, timezone
import time
import threading
from typing import Optional, Callable, Dict, Any, List

logger = logging.getLogger('AirQualityMonitor')


class ConsoleAlertSystem:
    """Console-based alert system"""

    def __init__(self):
        self.active_alerts = {}

    def send_alert(self, alert_type: str, message: str, severity: str = "medium",
                   metadata: Optional[Dict[str, Any]] = None) -> bool:
        alert_id = f"{alert_type}-{time.time()}"
        self.active_alerts[alert_id] = {
            'id': alert_id,
            'type': alert_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now(timezone.utc),
            'metadata': metadata or {}
        }
        print(f"🚨 ALERT [{severity.upper()}]: {message}")
        return True

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        return list(self.active_alerts.values())


class SimpleEventSystem:
    """Simple event system implementation"""

    def __init__(self):
        self.subscriptions = {}
        self.event_history = []

    def subscribe(self, event_type: str, callback: Callable) -> str:
        sub_id = f"{event_type}-{len(self.subscriptions) + 1}"
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = {}
        self.subscriptions[event_type][sub_id] = callback
        return sub_id

    def emit(self, event_type: str, data: Any) -> bool:
        # Record event
        event_record = {
            'type': event_type,
            'timestamp': datetime.now(timezone.utc),
            'data': data
        }
        self.event_history.append(event_record)

        # Notify subscribers
        if event_type in self.subscriptions:
            for callback in self.subscriptions[event_type].values():
                try:
                    callback(data)
                except Exception as e:
                    logger.error(f"Event callback failed: {e}")
        return True
