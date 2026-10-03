import os
import sys
from pathlib import Path

# Determine if running in a PyInstaller bundle
IS_FROZEN = getattr(sys, "frozen", False)

if IS_FROZEN:
    # Writable user data directory for packaged executable (%APPDATA%\ObsessionMatrix\data)
    app_data_dir = os.environ.get("APPDATA") or os.path.expanduser("~")
    DATA_DIR = Path(app_data_dir) / "ObsessionMatrix" / "data"
else:
    # Development data directory (local project /data folder)
    BASE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = BASE_DIR / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "obsession_matrix.db"

# Application Metadata
APP_TITLE = "Command Prompt - Obsession Matrix"
APP_VERSION = "1.0.0"

# Default Settings
DEFAULT_SETTINGS = {
    "notifications_enabled": "true",
    "notification_interval": "60",  # in minutes
    "notification_sound": "true",
    "theme": "classic-cmd",  # "classic-cmd", "matrix-green", "powershell-blue", "amber-crt"
    "paste_restriction": "true",
}

AVAILABLE_THEMES = ["classic-cmd", "matrix-green", "powershell-blue", "amber-crt"]
VALID_TASK_STATUSES = ["not_started", "in_progress", "done"]
