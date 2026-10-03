# Obsession Matrix — Terminal-Based Learning Management System

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GUI](https://img.shields.io/badge/GUI-PyWebView-6b46c1.svg)](https://pywebview.flowrl.com/)
[![Database](https://img.shields.io/badge/Database-SQLite3-003B57.svg)](https://www.sqlite.org/)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D6.svg)](https://www.microsoft.com/windows)
[![Tests](https://img.shields.io/badge/tests-14%20passed-brightgreen.svg)]()

Obsession Matrix is a distraction-free, terminal-based Learning Management System (LMS) built with Python, PyWebView, HTML/CSS/JavaScript, and SQLite. It combines the sleek aesthetic of a classic Windows Command Prompt / CRT terminal with a focused hierarchical framework designed for deep learning, skill mastery, and progress tracking.

---

## ⚡ Highlights & Features

- **Retro Command Prompt Interface**: Authentic CMD look and feel, scanline CRT shader overlay, and curated color themes (`classic-cmd`, `matrix-green`, `powershell-blue`, `amber-crt`).
- **Strict Hierarchical Directory Navigation**: Navigate knowledge domains like a file system (`cd <topic>`, `cd ..`, `back`, `ls`, `dir`). Dynamic breadcrumb prompt automatically tracks your current depth (e.g. `C:\OBSESSION_MATRIX\Cybersecurity\WebSec>`).
- **Cyclic & Hierarchy-Scoped Tab Auto-Completion**:
  - Press <kbd>Tab</kbd> to cycle forward through matches, or <kbd>Shift</kbd>+<kbd>Tab</kbd> to cycle backward.
  - When inside a topic, auto-completion is strictly scoped to the sub-topics belonging to that specific topic—no clutter from unrelated branches or root topics.
  - At root, auto-completion suggests available sections and main topics.
- **Immediate Dashboard Overview**: Running `cd dashboard` from anywhere instantly renders task counts, active tasks in progress, recent topics, and your primary Current Obsession without needing to run `ls`.
- **Direct Dashboard Navigation**: Jump directly into any topic or sub-topic displayed on the dashboard via `cd <name>`.
- **Root Menu Recall on `cd ..`**: Returning to the root prompt automatically displays the available main sections (`dashboard`, `interests`, `settings`).
- **Intentional Recall Guardrail**: Built-in clipboard paste restriction that encourages active recall and manual typing (can be toggled in settings).
- **Git-Style Progress Logging**: Record timestamped learning commits with title and description (`progress add "<title>" "<desc>"`), and review history (`progress view` or `git log`).
- **Desktop Toast Notifications**: Background daemon dispatches Windows notifications reminding you of your Current Obsession and in-progress tasks at configurable intervals.
- **Seamless APPDATA Persistence**: Packaged desktop builds automatically persist your SQLite database in `%APPDATA%\ObsessionMatrix\data` across restarts and upgrades.

---

## 💻 Commands Reference

### 🧭 Navigation & Views
| Command | Description |
| :--- | :--- |
| `dashboard` / `cd dashboard` | Open Dashboard Overview (renders immediately without `ls`) |
| `interests` / `cd interests` | Switch to Interests / Topics Hierarchy view |
| `settings` / `cd settings` | Switch to Application Settings view |
| `cd <topic_or_subtopic>` | Navigate into a specific topic or sub-topic folder (supports jumping from Dashboard) |
| `cd ..` / `back` | Return up one directory level (at root, prints the main menu options) |

### 📂 Topic & Task Creation
| Command | Description |
| :--- | :--- |
| `mkdir <name>` | Create a new sub-topic folder under the active topic |
| `touch <title>` | Create a new task under the active topic |
| `add interest "<name>"` | Create a new top-level interest topic |
| `add task "<topic>" "<title>"` | Create a task assigned to a specific topic |

### 🗑️ Deletion & Removal
| Command | Description |
| :--- | :--- |
| `rm <topic_name>` / `rmdir <name>` | Delete a topic folder and all its contents |
| `rm task <task_id>` | Delete a specific task by its ID number |
| `progress delete <index_or_title>` | Delete a progress log commit by index or title |

### 🎯 Focus & Obsession Management
| Command | Description |
| :--- | :--- |
| `current` | View full status of the active Current Obsession |
| `current set "<topic_name>"` | Set a topic as your primary Current Obsession |
| `current clear` | Clear the active Current Obsession |

### 📋 Task Lifecycle
| Command | Description |
| :--- | :--- |
| `done <task_id>` | Mark a task as completed by ID |
| `task status <task_id> <status>` | Set task status (`not_started`, `in_progress`, `done`) |

### 📝 Progress Logging (Git Commit Style)
| Command | Description |
| :--- | :--- |
| `progress add "<title>" "<desc>"` | Add a titled progress log entry with description |
| `progress view` | List all progress log commit titles for active topic |
| `progress view <number_or_title>` | View brief description and full details of an entry |
| `history` / `git log` | Alias for `progress view` |

### ⚙️ Application Settings (inside `settings`)
| Command | Description |
| :--- | :--- |
| `set <key> <value>` | Update a setting (e.g. `set theme matrix-green`) |
| `toggle <key>` | Toggle a boolean setting (e.g. `toggle paste_restriction`) |

### 🛠️ Terminal Utilities
| Command | Description |
| :--- | :--- |
| `ls` / `dir` | List contents and details of current location / Dashboard |
| `open <topic_name>` | Open detailed breakdown of a topic |
| `clear` | Clear terminal output screen |
| `help` | Display interactive help reference |
| `exit` | Close the desktop application window |
| `<Tab>` / `<Shift>+<Tab>` | Cycle forward / backward through auto-completed commands and scoped sub-topics |

---

## 🛠️ Requirements & Dependencies

- **Operating System**: Windows 10 / 11 (64-bit)
- **Python**: 3.10+ (for source execution & building)
- **Core Dependencies**:
  - `pywebview>=6.0.0`
  - `pythonnet>=3.0.0`
  - `plyer>=2.1.0`
  - `pyinstaller>=6.0.0`

Install all dependencies via pip:
```bash
pip install -r requirements.txt
```

---

## 🚀 Running from Source

To run the application directly from source:
```bash
python main.py
```

To run unit tests:
```bash
python run_tests.py
```

---

## 📦 Building Standalone Executable (.exe)

To build the standalone Windows executable:

### Option 1: One-Click Build Script
Run `build.bat` in the project root:
```cmd
build.bat
```

### Option 2: Manual PyInstaller Command
```cmd
pyinstaller --noconfirm ObsessionMatrix.spec
```

The compiled standalone application will be located at:
```text
dist/ObsessionMatrix/ObsessionMatrix.exe
```

---

## 💾 User Data Persistence

When running the standalone packaged `.exe`, user database records (interests, tasks, progress logs, and settings) are stored in the user's writable Windows Application Data directory:
```text
%APPDATA%\ObsessionMatrix\data\obsession_matrix.db
```
This ensures user data persists across application restarts and updates.

---

## 📁 Directory Structure

```text
├── backend/
│   ├── app_api.py               # PyWebView JavaScript bridge
│   ├── command_parser.py        # CLI command parser & navigation engine
│   ├── config.py                # App configuration & APPDATA path resolution
│   ├── database.py              # SQLite schema & migrations
│   ├── models.py                # Dataclass models
│   ├── notification_service.py  # Background desktop toast daemon
│   └── services.py              # Business logic & hierarchy management
├── frontend/
│   ├── app.js                   # Terminal stream controller, history & Tab cycling
│   ├── app_logo.ico             # Application window icon
│   ├── index.html               # CMD desktop window shell
│   └── styles.css               # CRT shader effects & theme styles
├── tests/
│   ├── test_commands.py         # Navigation, CLI, and lifecycle tests
│   ├── test_database.py         # DB migration & foreign key cascade tests
│   └── test_services.py         # Tree & progress service unit tests
├── build.bat                    # One-click Windows build script
├── main.py                      # Desktop application entry point
├── ObsessionMatrix.spec         # PyInstaller spec configuration
├── requirements.txt             # Python dependencies
└── run_tests.py                 # Test runner script
```

---

## 📄 License

This project is licensed under the MIT License.
