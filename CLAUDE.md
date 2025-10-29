# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python script that monitors system power draw and sends notifications when power consumption exceeds a user-defined threshold. This is designed to be a lightweight, standalone utility.

## Development Setup

Since this is a Python project, the typical development workflow will involve:

```bash
# Create virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Linux/Mac
# OR
.venv\Scripts\activate  # On Windows

# Install dependencies (once requirements.txt exists)
pip install -r requirements.txt

# Run the script (once implemented)
python powerdraw_notifier.py
```

## Architecture Considerations

The implementation should follow these patterns:

1. **Power Monitoring**: The core functionality needs to read power draw metrics from the system. On Linux, this typically involves reading from `/sys/class/power_supply/` or using tools like `powertop` or `sensors`. Platform-specific implementation may be needed.

2. **Configuration**: User-defined threshold should be configurable via:
   - Command-line arguments
   - Configuration file (e.g., YAML or JSON)
   - Environment variables

3. **Notification System**: Notifications should support multiple backends:
   - Desktop notifications (e.g., `notify-send` on Linux, `toast` on Windows)
   - Email notifications
   - Webhook/API calls (for integration with other services)

4. **Monitoring Loop**: The script should run continuously or be schedulable (cron/systemd timer) with configurable polling intervals.

## Key Implementation Notes

- The script should handle missing power metrics gracefully (not all systems expose power draw data in the same way)
- Consider using libraries like `psutil` for cross-platform system metrics access
- For desktop notifications, `plyer` or platform-specific tools can be used
- Logging should be implemented to track threshold violations and notification delivery
- The threshold configuration should support both absolute values (watts) and percentage-based thresholds
