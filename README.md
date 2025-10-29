# Power Monitor

**Cross-Platform Battery & Power Usage Monitor**

Power Monitor is a comprehensive desktop application that tracks battery power consumption, analyzes system resource usage, and provides real-time alerts for high power draw scenarios. With system tray integration, historical data logging, and interactive visualizations, it helps you understand and optimize your device's power efficiency.

## Features

- **Real-time Power Monitoring**: Continuously tracks battery status, power draw estimates, and system metrics
- **High Power Draw Detection with Root Cause Analysis**: Identifies abnormal power consumption and analyzes contributing factors (CPU, memory, disk, network, processes)
- **System Tray Integration**: Lightweight background operation with quick access to all features via system tray menu
- **Cross-Platform Notifications**: Desktop notifications for high power draw, low battery, and critical battery warnings
- **Historical Data Logging**: SQLite database stores power metrics with configurable retention periods
- **Interactive Power Usage Plots**: Visualize power consumption trends with matplotlib-powered charts
- **Configurable Thresholds and Settings**: Customize monitoring intervals, power thresholds, battery warnings, and notification preferences
- **Resource Tracking**: Monitor CPU usage, memory consumption, disk I/O, network activity, and top power-consuming processes

## Screenshots

### System Tray Menu
*The application lives in your system tray, providing quick access to statistics, visualizations, and settings.*

### Statistics Window
*View real-time system metrics including battery status, power draw, CPU/memory usage, and active processes.*

### Power Curve Visualization
*Interactive plots show historical power consumption trends over various time periods (1h, 6h, 24h, 7d).*

### Settings Dialog
*Configure monitoring intervals, power thresholds, battery warnings, notification preferences, and data retention.*

## Requirements

- **Python**: 3.8 or higher
- **Operating System**: Windows, macOS, or Linux
- **Hardware**: Device with battery/power monitoring support (laptops, portable devices)
- **Display**: GUI required for system tray and dialogs

## Installation

### Running from Source

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/powerdraw_notifier.git
   cd powerdraw_notifier
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install psutil pystray Pillow plyer matplotlib pandas
   ```

4. **Generate application icons** (optional):
   ```bash
   python generate_icons.py
   ```

5. **Run the application**:
   ```bash
   python -m power_monitor.main
   ```

## Building from Source

Power Monitor can be built into standalone executables for distribution using PyInstaller.

### Prerequisites

Install development dependencies:
```bash
pip install pyinstaller
```

### Building for Windows

Run the Windows build script:
```batch
cd build_scripts
build_windows.bat
```

The executable will be created in `dist\PowerMonitor\PowerMonitor.exe`.

### Building for macOS

Run the macOS build script:
```bash
cd build_scripts
chmod +x build_mac.sh
./build_mac.sh
```

The application bundle will be created in `dist/PowerMonitor/`.

### Building for Linux

Run the Linux build script:
```bash
cd build_scripts
chmod +x build_linux.sh
./build_linux.sh
```

The executable will be created in `dist/PowerMonitor/PowerMonitor`.

## Configuration

Power Monitor uses a `config.json` file for persistent settings. If no configuration file exists, default values are used automatically.

### Configuration File Location

Place `config.json` in the same directory as the executable or Python script.

### Configuration Options

| Option | Type | Default | Range | Description |
|--------|------|---------|-------|-------------|
| `monitoring_interval_seconds` | number | 30 | 5-300 | How often to collect power metrics (seconds) |
| `high_power_threshold_percent_per_10min` | number | 2.0 | 0.1-50.0 | Battery drain threshold for high power alert (% per 10 minutes) |
| `low_battery_warning_percent` | number | 20 | 5-50 | Battery level for low battery warning (%) |
| `critical_battery_percent` | number | 10 | 1-20 | Battery level for critical battery alert (%) |
| `notification_cooldown_minutes` | number | 15 | 1-120 | Minimum time between similar notifications (minutes) |
| `data_retention_days` | number | 30 | 1-365 | How long to keep historical data (days) |
| `log_level` | string | "INFO" | See below | Logging verbosity level |
| `enable_notifications` | boolean | true | - | Enable/disable desktop notifications |
| `auto_start_monitoring` | boolean | true | - | Start monitoring automatically on launch |

### Valid Log Levels

- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages (recommended)
- `WARNING`: Warning messages for potentially harmful situations
- `ERROR`: Error messages for serious problems
- `CRITICAL`: Critical messages for very serious errors

### Example Configuration

```json
{
  "monitoring_interval_seconds": 30,
  "high_power_threshold_percent_per_10min": 2.0,
  "low_battery_warning_percent": 20,
  "critical_battery_percent": 10,
  "notification_cooldown_minutes": 15,
  "data_retention_days": 30,
  "log_level": "INFO",
  "enable_notifications": true,
  "auto_start_monitoring": true
}
```

## Usage

### Running the Application

**From Source**:
```bash
python -m power_monitor.main
```

**From Built Executable**:
- Windows: Double-click `PowerMonitor.exe`
- macOS: Open `PowerMonitor.app` or run `./PowerMonitor`
- Linux: Run `./PowerMonitor` from terminal

The application runs in the background with an icon in the system tray (notification area on Windows, menu bar on macOS, system tray on Linux).

### System Tray Menu Options

Right-click (Windows/Linux) or click (macOS) the system tray icon to access:

- **Current Stats**: Opens a window showing real-time system metrics
  - Battery status (percentage, charging state, time remaining)
  - Power draw estimate
  - CPU usage (overall and per-core)
  - Memory usage
  - Disk and network I/O rates
  - Top 5 power-consuming processes

- **View Power Curve**: Opens visualization window with historical power data
  - Interactive matplotlib plots
  - Multiple time ranges: 1 hour, 6 hours, 24 hours, 7 days
  - Battery percentage trends
  - Power draw estimation over time

- **Settings**: Opens configuration dialog
  - Adjust monitoring interval
  - Set power draw thresholds
  - Configure battery warning levels
  - Enable/disable notifications
  - Set notification cooldown period
  - Configure data retention

- **Open Logs Folder**: Opens the folder containing application logs
  - Useful for troubleshooting
  - Logs rotated daily with retention policy

- **About**: Shows application version and information

- **Quit**: Gracefully shuts down the application

### Viewing Statistics

1. Click the system tray icon
2. Select "Current Stats"
3. View real-time metrics in the statistics window
4. Click "Refresh" to update data manually
5. Close the window when done (monitoring continues in background)

### Viewing Power Curves

1. Click the system tray icon
2. Select "View Power Curve"
3. Choose a time range from the buttons (1h, 6h, 24h, 7d)
4. The plot updates to show historical power data for that period
5. Use matplotlib's built-in tools to zoom, pan, and inspect data points

### Adjusting Settings

1. Click the system tray icon
2. Select "Settings"
3. Modify any configuration values
4. Click "Save" to apply changes
5. Click "Reset to Defaults" to restore default values
6. Click "Cancel" to discard changes

Settings are saved to `config.json` and take effect immediately. If monitoring is active, it will restart to apply the new monitoring interval.

## Architecture

Power Monitor is built with a modular architecture consisting of several key components:

### Core Components

- **PowerMonitor** (`monitor.py`): Data collection engine
  - Uses `psutil` to gather system metrics
  - Tracks battery status, CPU, memory, disk I/O, network I/O
  - Estimates power draw based on battery percentage changes
  - Runs in background thread with configurable intervals

- **PowerAnalyzer** (`analyzer.py`): Analysis and intelligence
  - Detects high power draw conditions
  - Performs root cause analysis
  - Identifies top power-consuming processes
  - Correlates resource usage with power consumption

- **PowerNotifier** (`notifier.py`): Notification system
  - Cross-platform desktop notifications via `plyer`
  - Notification cooldown to prevent spam
  - Supports high power, low battery, and critical battery alerts

- **PowerPlotter** (`plotter.py`): Data visualization
  - Creates interactive plots using `matplotlib`
  - Supports multiple time ranges
  - Visualizes battery percentage and power draw trends

- **PowerDatabase** (`database.py`): Data persistence
  - SQLite database for historical metrics
  - Thread-safe operations
  - Automatic data cleanup based on retention policy
  - Efficient querying for time-range analysis

- **ConfigManager** (`config.py`): Configuration management
  - JSON-based configuration with validation
  - Thread-safe read/write operations
  - Default values and range constraints
  - Runtime configuration updates

### User Interface

- **System Tray Icon** (`main.py`): Using `pystray`
  - Cross-platform system tray integration
  - Dynamic icon updates (normal/alert states)
  - Context menu for all application features

- **UI Windows** (`ui/` directory): Built with `tkinter`
  - `StatsWindow`: Real-time statistics display
  - `PlotWindow`: Interactive power curve visualization
  - `SettingsWindow`: Configuration editor with validation

### Supporting Components

- **Logger** (`logger.py`): Centralized logging
  - Rotating file handlers
  - Configurable log levels
  - Separate logs per module

- **Icon Generator** (`generate_icons.py`): Asset creation
  - Generates battery icons programmatically using `Pillow`
  - Creates normal and alert state icons

## Development

### Project Structure

```
powerdraw_notifier/
├── power_monitor/           # Main application package
│   ├── __init__.py         # Package initialization
│   ├── main.py             # Application entry point
│   ├── monitor.py          # Power monitoring logic
│   ├── analyzer.py         # Power analysis algorithms
│   ├── notifier.py         # Notification system
│   ├── plotter.py          # Data visualization
│   ├── database.py         # SQLite data storage
│   ├── config.py           # Configuration management
│   ├── logger.py           # Logging setup
│   └── ui/                 # User interface windows
│       ├── __init__.py
│       ├── stats_window.py
│       ├── plot_window.py
│       └── settings_window.py
├── build_scripts/           # Build automation scripts
│   ├── build_windows.bat   # Windows build script
│   ├── build_mac.sh        # macOS build script
│   └── build_linux.sh      # Linux build script
├── assets/                  # Application resources
│   ├── icon.png            # Normal tray icon
│   └── icon_alert.png      # Alert tray icon
├── data/                    # Runtime data directory
│   ├── power_history.db    # SQLite database
│   └── logs/               # Application logs
├── generate_icons.py        # Icon generation utility
├── PowerMonitor.spec        # PyInstaller specification
├── config.json             # User configuration (created at runtime)
├── LICENSE                 # MIT License
└── README.md               # This file
```

### Running in Development Mode

1. **Set up development environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Enable debug logging**:
   Edit `config.json` or create one:
   ```json
   {
     "log_level": "DEBUG"
   }
   ```

3. **Run from source**:
   ```bash
   python -m power_monitor.main
   ```

4. **View logs**:
   Logs are written to `data/logs/power_monitor_YYYY-MM-DD.log`

### Adding Features

When adding new features:

1. **Follow the modular architecture**: Keep components focused and loosely coupled
2. **Use the existing configuration system**: Add new settings to `ConfigManager.DEFAULT_CONFIG`
3. **Implement proper logging**: Use the module-specific logger for debugging
4. **Handle errors gracefully**: Use try-except blocks and log exceptions
5. **Maintain thread safety**: Use locks for shared resources
6. **Update the UI**: Add menu items or windows as needed
7. **Test cross-platform**: Verify functionality on Windows, macOS, and Linux
8. **Document changes**: Update this README and add code comments

## Troubleshooting

### No Battery Detected

**Symptom**: Application shows "No battery detected" or fails to start.

**Solutions**:
- Ensure you're running on a device with a battery (laptop, portable device)
- Check that the battery is properly connected
- Verify that your OS recognizes the battery (check system settings)
- On Linux, ensure `upower` or battery monitoring tools are installed
- Try running with elevated privileges (though this shouldn't be necessary)

### Notifications Not Working

**Symptom**: Desktop notifications don't appear.

**Solutions**:
- Check that `enable_notifications` is `true` in `config.json`
- Verify notification permissions in your OS settings:
  - Windows: Settings > System > Notifications
  - macOS: System Preferences > Notifications
  - Linux: Check notification daemon (notification-daemon, dunst, etc.)
- Increase the cooldown period if notifications seem missing (they may be rate-limited)
- Check logs for notification errors: `data/logs/`

### Icon Not Displaying

**Symptom**: System tray icon is missing or shows a placeholder.

**Solutions**:
- Ensure icon files exist in `assets/` directory:
  - `assets/icon.png`
  - `assets/icon_alert.png`
- Run `python generate_icons.py` to regenerate icons
- Check that Pillow is properly installed: `pip install --upgrade Pillow`
- Verify the system tray is visible on your desktop environment
- On Linux, ensure you have a system tray implementation (libappindicator)
- Check logs for icon loading errors

### PyInstaller Build Issues

**Symptom**: Build fails or executable doesn't run.

**Solutions**:
- Ensure PyInstaller is installed: `pip install pyinstaller`
- Clean previous builds: delete `build/` and `dist/` directories
- Verify all dependencies are installed
- Check that icon files exist before building
- Review `PowerMonitor.spec` for correct paths
- On Windows, disable antivirus temporarily during build
- On macOS, check Gatekeeper settings if app won't open
- On Linux, ensure executable permissions: `chmod +x dist/PowerMonitor/PowerMonitor`
- Check build logs for specific errors
- Try rebuilding in a fresh virtual environment

### Application Crashes on Startup

**Symptom**: Application starts but immediately crashes.

**Solutions**:
- Check logs in `data/logs/` for error messages
- Delete `config.json` to reset to defaults
- Ensure all dependencies are installed correctly
- Verify Python version is 3.8 or higher
- Check that no other instance is running
- Delete `data/power_history.db` if database is corrupted
- Run from terminal to see error output

### High CPU Usage

**Symptom**: Power Monitor itself consumes excessive CPU.

**Solutions**:
- Increase `monitoring_interval_seconds` in settings (e.g., 60-120 seconds)
- Check if multiple instances are running
- Review top processes in the statistics window
- Close the power curve visualization window when not in use
- Ensure you're running the latest version
- Check for disk I/O issues that might slow database operations

## License

This project is licensed under the **MIT License**.

Copyright (c) 2025

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## Contributing

Contributions are welcome! Here's how you can help:

### Reporting Bugs

1. Check if the issue already exists in the issue tracker
2. Include detailed information:
   - Operating system and version
   - Python version
   - Steps to reproduce
   - Expected vs actual behavior
   - Log files from `data/logs/`
   - Screenshots if applicable

### Suggesting Features

1. Open an issue describing the feature
2. Explain the use case and benefits
3. Discuss implementation approaches
4. Be open to feedback and alternatives

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes following the project's coding style
4. Test thoroughly on multiple platforms if possible
5. Update documentation (README, docstrings, comments)
6. Commit with clear, descriptive messages
7. Push to your fork: `git push origin feature/your-feature-name`
8. Open a pull request with:
   - Description of changes
   - Related issue numbers
   - Testing performed
   - Screenshots/examples if applicable

### Development Guidelines

- Follow PEP 8 style guidelines
- Write docstrings for all public functions and classes
- Add type hints where appropriate
- Keep functions focused and modular
- Handle errors gracefully with appropriate logging
- Test on Windows, macOS, and Linux when possible
- Update documentation for user-facing changes

## Credits

Power Monitor is built with the following excellent open-source libraries:

- **[psutil](https://github.com/giampaolo/psutil)**: Cross-platform system and process utilities
- **[pystray](https://github.com/moses-palmer/pystray)**: System tray icon support for Windows, macOS, and Linux
- **[plyer](https://github.com/kivy/plyer)**: Cross-platform desktop notifications
- **[matplotlib](https://matplotlib.org/)**: Data visualization and plotting
- **[pandas](https://pandas.pydata.org/)**: Data analysis and time-series handling
- **[Pillow (PIL)](https://python-pillow.org/)**: Image processing and icon generation

Special thanks to the maintainers and contributors of these projects for making cross-platform Python development possible.

---

**Power Monitor** - Keep your battery usage in check!
