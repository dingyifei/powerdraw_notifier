# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Power Monitor** is a cross-platform (Windows/macOS/Linux) system tray application that monitors power usage, identifies causes of high power draw, sends notifications, logs historical data, and provides visualization through interactive plots. The application is packaged as a standalone executable using PyInstaller.

### Key Features
- Real-time power and system resource monitoring
- High power draw detection with root cause analysis
- Cross-platform desktop notifications
- SQLite database for historical data storage
- Interactive matplotlib visualizations
- System tray integration with pystray
- Configurable thresholds and settings

## Development Setup

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd powerdraw_notifier

# Create and activate virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Generate icons (if not already generated)
python generate_icons.py

# Run from source
python -m power_monitor.main
```

### Code Quality & Linting

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and code formatting. Ruff is an extremely fast Python linter and formatter written in Rust.

```bash
# Install development dependencies (includes ruff)
pip install -r requirements-dev.txt

# Run linter
ruff check power_monitor/ generate_icons.py

# Auto-fix issues
ruff check --fix power_monitor/ generate_icons.py

# Format code
ruff format power_monitor/ generate_icons.py

# Check a specific file
ruff check power_monitor/main.py
```

Configuration is stored in `pyproject.toml` with project-specific rules and exclusions.

### CI/CD Workflows

This project uses GitHub Actions for continuous integration and deployment:

#### Ruff Code Quality Workflow
- **File**: `.github/workflows/ruff.yml`
- **Triggers**: Push/PR to main or develop branches (when .py files change)
- **Actions**:
  - Runs `ruff check` to detect code quality issues
  - Runs `ruff format --check` to verify code formatting
  - Reports issues directly in GitHub UI using annotations
- **Purpose**: Ensures all code meets quality standards before merging

#### Windows Build Workflow
- **File**: `.github/workflows/windows-build.yml`
- **Triggers**:
  - Push to main branch
  - Version tags (v*)
  - Manual dispatch
  - Pull requests to main
- **Actions**:
  - Builds Windows executable with PyInstaller
  - Generates application icons
  - Verifies build artifacts
  - Creates versioned ZIP archive
  - Uploads artifacts (30-day retention)
  - Automatically creates GitHub releases for tagged versions
- **Purpose**: Automated Windows executable packaging and distribution

To trigger a release build, create and push a version tag:
```bash
git tag v1.0.0
git push origin v1.0.0
```

### Building Executables

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Windows
build_scripts\build_windows.bat

# macOS
./build_scripts/build_mac.sh

# Linux
./build_scripts/build_linux.sh
```

## Project Structure

```
powerdraw_notifier/
├── .github/                    # GitHub configuration
│   └── workflows/              # GitHub Actions workflows
│       ├── ruff.yml            # Code quality checks
│       └── windows-build.yml   # Windows executable build
├── power_monitor/              # Main application package
│   ├── __init__.py
│   ├── main.py                 # Entry point & system tray
│   ├── monitor.py              # psutil-based data collection
│   ├── analyzer.py             # Power draw analysis
│   ├── notifier.py             # Cross-platform notifications
│   ├── plotter.py              # Matplotlib visualizations
│   ├── logger.py               # Logging & data cleanup
│   ├── database.py             # SQLite operations
│   ├── config.py               # Configuration management
│   └── ui/                     # Tkinter UI components
│       ├── __init__.py
│       ├── settings_window.py  # Settings dialog
│       ├── stats_window.py     # Current stats display
│       └── plot_window.py      # Matplotlib plot window
├── data/                       # Runtime data (git-ignored)
│   ├── logs/                   # Application logs
│   └── power_history.db        # SQLite database
├── assets/                     # Static resources
│   ├── icon.png                # Normal tray icon
│   └── icon_alert.png          # Alert tray icon
├── build_scripts/              # PyInstaller build scripts
│   ├── build_windows.bat
│   ├── build_mac.sh
│   └── build_linux.sh
├── config.json                 # User configuration
├── requirements.txt            # Runtime dependencies
├── requirements-dev.txt        # Development dependencies
├── pyproject.toml              # Project metadata and ruff config
├── PowerMonitor.spec           # PyInstaller spec file
├── generate_icons.py           # Icon generation script
├── README.md                   # User documentation
└── CLAUDE.md                   # This file
```

## Architecture

### Core Components

#### 1. **PowerMonitor** (monitor.py)
- Uses psutil to collect system metrics every N seconds
- Collects: battery status, CPU usage, memory usage, disk I/O, network I/O, top processes
- Calculates power draw estimate from battery percentage changes
- Runs in background thread with clean shutdown via threading.Event()
- Thread-safe data collection and storage

**Key Methods:**
- `start()` / `stop()` - Control monitoring thread
- `collect_metrics()` - Gather all system metrics
- `get_current_stats()` - Synchronous stats for UI

#### 2. **PowerAnalyzer** (analyzer.py)
- Analyzes metrics to identify high power draw causes
- Calculates rolling averages from database
- Ranks causes by severity: HIGH_CPU, HIGH_DISK_IO, HIGH_NETWORK, MULTIPLE_PROCESSES
- Provides confidence scores and actionable recommendations

**Detection Thresholds:**
- High CPU: Total > 50% OR any process > 25%
- High Disk I/O: Read+write > 50 MB/s
- High Network: Sent+received > 10 MB/s

#### 3. **PowerNotifier** (notifier.py)
- Cross-platform notifications using plyer
- Notification types: LOW_BATTERY, CRITICAL_BATTERY, HIGH_POWER_DRAW, UNUSUAL_DRAIN
- Implements cooldown system to prevent spam
- Handles platform-specific icon formats (.ico for Windows, .png for others)
- Fallback implementation for PyInstaller builds

#### 4. **PowerPlotter** (plotter.py)
- Generates matplotlib figures with 3 subplots:
  1. Battery percentage over time (color-coded zones)
  2. Power draw estimate with high draw annotations
  3. CPU usage with threshold lines
- Exports plots to PNG
- Thread-safe with 'Agg' backend

#### 5. **PowerDatabase** (database.py)
- Thread-safe SQLite operations
- Tables: `power_metrics`, `high_power_events`
- Methods for inserting, querying, and cleaning data
- Returns pandas DataFrames for plotting

#### 6. **ConfigManager** (config.py)
- Thread-safe configuration management
- Loads from config.json with defaults
- Validates all configuration values
- Supports runtime updates and persistence

#### 7. **UI Components** (ui/)
- **SettingsWindow**: Configuration dialog with form validation
- **StatsWindow**: Real-time stats display with auto-refresh
- **PlotWindow**: Embedded matplotlib with toolbar and controls

#### 8. **SyncthingClient** (syncthing_client.py)
- REST API client for Syncthing integration
- Thread-safe operations with automatic error handling
- Methods:
  - `get_device_id()` - Retrieve local device ID
  - `is_paused()` - Check current pause state
  - `pause_device()` - Pause local device sync
  - `resume_device()` - Resume local device sync
  - `test_connection()` - Validate API key and connectivity
  - `get_status_text()` - Get human-readable status for UI
- Uses requests library with 5-second timeout
- Custom exceptions: `SyncthingError`, `SyncthingConnectionError`, `SyncthingAPIError`
- Connects to localhost:8384 by default

#### 9. **Main Application** (main.py)
- System tray icon with pystray
- Menu: Stats, Plots, Syncthing (optional), Settings, Logs, About, Quit
- Dynamic icon switching (normal ↔ alert)
- Dynamic Syncthing menu item showing current status
- Graceful shutdown handling
- Signal handlers for SIGINT/SIGTERM

## Configuration Reference

All settings are stored in `config.json`:

| Setting | Type | Default | Range | Description |
|---------|------|---------|-------|-------------|
| `monitoring_interval_seconds` | int | 30 | 5-300 | Time between metric collections |
| `high_power_threshold_percent_per_10min` | float | 2.0 | 0.1-50.0 | Power draw threshold (% per 10 min) |
| `low_battery_warning_percent` | int | 20 | 5-50 | Low battery notification threshold |
| `critical_battery_percent` | int | 10 | 1-20 | Critical battery notification threshold |
| `notification_cooldown_minutes` | int | 15 | 1-120 | Minimum time between notifications |
| `data_retention_days` | int | 30 | 1-365 | How long to keep historical data |
| `log_level` | str | INFO | DEBUG, INFO, WARNING, ERROR, CRITICAL | Logging verbosity |
| `enable_notifications` | bool | true | - | Enable/disable all notifications |
| `auto_start_monitoring` | bool | true | - | Start monitoring on app launch |
| `syncthing_enabled` | bool | false | - | Enable Syncthing integration |
| `syncthing_api_key` | str | "" | - | Syncthing REST API key |

## Database Schema

### power_metrics Table
```sql
CREATE TABLE power_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    battery_percent REAL,
    power_plugged INTEGER,
    power_draw_estimate REAL,
    cpu_percent REAL,
    memory_percent REAL,
    disk_read_mb REAL,
    disk_write_mb REAL,
    network_sent_mb REAL,
    network_recv_mb REAL,
    top_process_name TEXT,
    top_process_cpu REAL
);
CREATE INDEX idx_timestamp ON power_metrics(timestamp);
```

### high_power_events Table
```sql
CREATE TABLE high_power_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp INTEGER NOT NULL,
    duration_seconds INTEGER,
    primary_cause TEXT,
    processes_involved TEXT,
    avg_power_draw REAL
);
```

## Key Implementation Details

### Thread Safety
- All components use threading.Lock() for shared resource access
- psutil operations are thread-safe as of version 5.9.6+
- GUI updates use `window.after()` for thread safety
- Matplotlib uses 'Agg' backend for non-GUI operation

### Power Draw Calculation
```python
# Formula:
power_draw = (battery_prev - battery_now) / hours_elapsed
# Returns: percentage per hour
# Only calculated when on battery power (not plugged in)
```

### High DPI Display Support
The application automatically detects and configures for high DPI displays on Windows:

**DPI Awareness:**
- Enables per-monitor DPI awareness v2 on Windows 10+ for crisp rendering
- Falls back to per-monitor DPI awareness v1 on Windows 8.1
- Falls back to system DPI awareness on Windows Vista/7
- Called before any tkinter windows are created

**Tkinter Scaling:**
- Automatically detects system DPI (default: 96 DPI = 100% scaling)
- Applies appropriate scaling factor to all tkinter windows
- Scaling factor = (System DPI / 96) × 1.33
- Logged at application startup for debugging

**Benefits:**
- Text and UI elements render sharply on high DPI monitors
- Proper ClearType font rendering on Windows
- Consistent sizing across different DPI settings

### Cross-Platform Considerations

**Windows:**
- Icon format: .ico (converted from .png)
- File explorer: `os.startfile()`
- pystray can use threading

**macOS:**
- Icon format: .png
- File explorer: `open` command
- pystray must run on main thread
- Notifications use deprecated NSUserNotificationCenter

**Linux:**
- Icon format: .png
- File explorer: `xdg-open` command
- Multiple pystray backends: AppIndicator (preferred), GTK, Xorg
- Install PyGObject for AppIndicator support

### PyInstaller Notes
- Hidden imports required for pystray and plyer platform modules
- Resources bundled via `datas` parameter
- Access bundled files with `sys._MEIPASS`
- Console disabled for windowed application

## Development Guidelines

### Adding New Features

1. **New Metrics**: Add to `PowerMonitor.collect_metrics()` and database schema
2. **New Analysis**: Extend `PowerAnalyzer.identify_causes()` with new cause types
3. **New Notifications**: Add to `PowerNotifier` with new notification type
4. **New UI**: Create new window class in `ui/` package

### Code Style
- Follow PEP 8 standards (enforced by Ruff)
- Use type hints where appropriate
- Docstrings for all public methods
- Logging for debugging and error tracking
- Run `ruff check --fix` and `ruff format` before committing
- Line length: 100 characters maximum
- Import sorting: standard library → third-party → first-party → local

### Testing Checklist
- [ ] Monitoring starts and collects data
- [ ] Database stores and retrieves data correctly
- [ ] Notifications trigger on conditions
- [ ] Plots display correctly with data
- [ ] Settings save and apply
- [ ] System tray menu items work
- [ ] Clean shutdown (no hanging threads)
- [ ] PyInstaller build runs correctly
- [ ] Handles missing battery gracefully

## Troubleshooting

### Common Issues

**No Battery Detected:**
- The app detects when no battery exists and shows appropriate messages
- Desktop PCs without batteries will still show CPU/memory/disk/network stats

**Notifications Not Working:**
- Check `enable_notifications` in config.json
- On Linux, ensure notification daemon is running
- On macOS, may require system notification permissions

**High Power Draw False Positives:**
- Adjust `high_power_threshold_percent_per_10min` in settings
- Check analyzer thresholds in analyzer.py

**PyInstaller Build Issues:**
- Ensure all hidden imports are in PowerMonitor.spec
- Check that assets/ directory contains both icons
- Verify Python version compatibility (3.8+)

## Dependencies

### Runtime Dependencies
- **psutil**: System and process monitoring
- **pystray**: System tray icon (cross-platform)
- **plyer**: Desktop notifications (cross-platform)
- **Pillow (PIL)**: Image handling and icon generation
- **matplotlib**: Data visualization
- **pandas**: Data manipulation for plotting
- **requests**: HTTP client for Syncthing API integration

### Development Dependencies
- **pyinstaller**: Executable packaging
- **ruff**: Fast Python linter and formatter (replaces flake8, black, isort, etc.)

## License

This project is licensed under the MIT License. See README.md for full license text.

## Contributing

When contributing to this codebase:
1. Follow the existing code structure and conventions
2. Add appropriate logging for new features
3. Update configuration schema if adding new settings
4. Test on multiple platforms when possible
5. Update README.md and this file with significant changes

## Contact & Support

For issues, feature requests, or questions:
- Check the Troubleshooting section above
- Review README.md for usage documentation
- Check application logs in `data/logs/`
- Consult psutil/pystray/plyer documentation for platform-specific issues
