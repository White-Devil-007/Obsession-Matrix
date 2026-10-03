import time
import threading
from typing import Optional
from backend.services import AppService
from backend.database import get_db

try:
    from plyer import notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

class NotificationDaemon(threading.Thread):
    def __init__(self, service: Optional[AppService] = None, check_interval_sec: int = 15):
        super().__init__(daemon=True)
        self.service = service or AppService(get_db())
        self.check_interval_sec = check_interval_sec
        self.running = True
        self.last_notified_time = 0

    def run(self):
        while self.running:
            try:
                self._check_and_notify()
            except Exception as e:
                # Daemon resilience
                pass
            time.sleep(self.check_interval_sec)

    def stop(self):
        self.running = False

    def trigger_test_notification(self) -> bool:
        return self._send_toast(
            title="OBSESSION MATRIX // System Test",
            message="Local Windows Toast Notification working successfully!"
        )

    def _check_and_notify(self):
        settings = self.service.get_all_settings()
        enabled = settings.get("notifications_enabled", "true") == "true"
        if not enabled:
            return

        interval_minutes = int(settings.get("notification_interval", "60"))
        interval_seconds = interval_minutes * 60

        now = time.time()
        if (now - self.last_notified_time) < interval_seconds:
            return

        summary = self.service.get_dashboard_summary()
        obsession = summary.get("current_obsession")
        in_prog_tasks = summary.get("in_progress_tasks", [])

        if not obsession and not in_prog_tasks:
            return

        title = "OBSESSION MATRIX // Focus Update"
        lines = []
        if obsession:
            lines.append(f"Obsession: {obsession['name']} ({obsession['custom_progress']})")
        if in_prog_tasks:
            lines.append(f"In Progress: {len(in_prog_tasks)} task(s) active")

        msg = " | ".join(lines)
        if self._send_toast(title, msg):
            self.last_notified_time = now

    def _send_toast(self, title: str, message: str) -> bool:
        if PLYER_AVAILABLE:
            try:
                notification.notify(
                    title=title,
                    message=message,
                    app_name="Obsession Matrix",
                    timeout=5
                )
                return True
            except Exception:
                return False
        return False
