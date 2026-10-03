import os
import sys
from pathlib import Path
import webview
from backend.database import get_db
from backend.services import AppService
from backend.app_api import AppApi
from backend.notification_service import NotificationDaemon
from backend.config import APP_TITLE

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent

def main():
    # Initialize Database & Core Services
    db = get_db()
    service = AppService(db)
    api = AppApi(service)

    # Start Background Notification Daemon Thread
    notification_daemon = NotificationDaemon(service=service, check_interval_sec=30)
    notification_daemon.start()

    # Path to frontend index.html
    base_dir = get_base_dir()
    frontend_path = base_dir / "frontend" / "index.html"
    if not frontend_path.exists():
        print(f"Error: Frontend index.html not found at {frontend_path}")
        sys.exit(1)

    # Create PyWebView Desktop Window
    window = webview.create_window(
        title=APP_TITLE,
        url=str(frontend_path),
        js_api=api,
        width=1240,
        height=820,
        min_size=(940, 640),
        background_color='#000000'
    )

    # Launch Application Loop
    webview.start(debug=False)

    # Cleanup on exit
    notification_daemon.stop()

if __name__ == "__main__":
    main()
