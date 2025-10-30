"""
Entry point for Power Monitor application with system tray icon.

Orchestrates all components and provides a system tray interface for monitoring
battery power draw and system resources.
"""

import os
import platform
import signal
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Optional

import pystray
from PIL import Image

# Import all components
from power_monitor.analyzer import PowerAnalyzer
from power_monitor.config import ConfigManager
from power_monitor.database import PowerDatabase
from power_monitor.logger import setup_logging
from power_monitor.monitor import PowerMonitor
from power_monitor.notifier import PowerNotifier
from power_monitor.plotter import PowerPlotter

# Import UI components
from power_monitor.ui.plot_window import PlotWindow
from power_monitor.ui.settings_window import SettingsWindow
from power_monitor.ui.stats_window import StatsWindow


class PowerMonitorApp:
    """Main application class with system tray icon."""

    def __init__(self):
        """Initialize the Power Monitor application."""
        # Determine base path for bundled resources (PyInstaller)
        if getattr(sys, "frozen", False):
            # Running as compiled executable
            self.base_path = Path(sys._MEIPASS)
        else:
            # Running in normal Python environment
            self.base_path = Path(__file__).parent.parent

        # Initialize components
        self.config = ConfigManager("config.json")
        self.database = PowerDatabase("data/power_history.db")
        self.logger = setup_logging(self.config, "data/logs")

        self.monitor = PowerMonitor(self.config, self.database)
        self.analyzer = PowerAnalyzer(self.config, self.database)
        self.notifier = PowerNotifier(self.config)
        self.plotter = PowerPlotter(self.database)

        # Threading control
        self.shutdown_event = threading.Event()
        self.analysis_thread = None
        self.is_high_power_alert = False

        # High power event tracking
        self.high_power_event_start = None
        self.high_power_event_data = []

        # Hidden Tkinter root window (required for dialogs)
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the root window

        # Start Tkinter event loop processing
        self._process_tk_events()

        # System tray icon
        self.icon = None
        self.icon_normal_path = self.base_path / "assets" / "icon.png"
        self.icon_alert_path = self.base_path / "assets" / "icon_alert.png"

        self.logger.info("=" * 60)
        self.logger.info("Power Monitor Application Initialized")
        self.logger.info(f"Base path: {self.base_path}")
        self.logger.info(f"Platform: {platform.system()}")
        self.logger.info("=" * 60)

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.shutdown()

    def _process_tk_events(self):
        """Process Tkinter events to keep the GUI responsive."""
        try:
            self.root.update()
        except tk.TclError:
            # Root window was destroyed
            return
        except Exception as e:
            self.logger.error(f"Error processing Tkinter events: {e}")

        # Schedule next event processing (every 100ms)
        if not self.shutdown_event.is_set():
            self.root.after(100, self._process_tk_events)

    def _load_icon_image(self, path: Path) -> Optional[Image.Image]:
        """
        Load icon image from file.

        Args:
            path: Path to icon file

        Returns:
            PIL Image object, or None if failed
        """
        try:
            if not path.exists():
                self.logger.error(f"Icon file not found: {path}")
                return None

            image = Image.open(path)
            self.logger.debug(f"Loaded icon: {path}")
            return image

        except Exception as e:
            self.logger.error(f"Error loading icon from {path}: {e}", exc_info=True)
            return None

    def _update_tray_icon(self, alert: bool = False):
        """
        Update system tray icon based on alert state.

        Args:
            alert: True to show alert icon, False for normal icon
        """
        if self.icon is None:
            return

        try:
            icon_path = self.icon_alert_path if alert else self.icon_normal_path
            new_image = self._load_icon_image(icon_path)

            if new_image:
                self.icon.icon = new_image
                self.is_high_power_alert = alert
                self.logger.debug(f"Tray icon updated: alert={alert}")

        except Exception as e:
            self.logger.error(f"Error updating tray icon: {e}", exc_info=True)

    def _check_high_power_draw(self):
        """Periodically check for high power draw and update icon."""
        while not self.shutdown_event.is_set():
            try:
                # Get current metrics
                metrics = self.monitor.get_current_stats()

                if metrics:
                    # Analyze power draw
                    power_draw = metrics.get("power_draw_estimate", 0.0)
                    is_high = self.analyzer.is_high_power_draw(power_draw)

                    # Update icon if state changed
                    if is_high != self.is_high_power_alert:
                        self._update_tray_icon(alert=is_high)

                        # Send notification if high power detected
                        if is_high:
                            # Starting a high power event
                            self.high_power_event_start = time.time()
                            self.high_power_event_data = []

                            if self.config.get("enable_notifications", True):
                                analysis = self.analyzer.analyze_current_state(metrics)
                                battery_percent = metrics.get("battery_percent", 0)
                                self.notifier.notify_high_power_draw(analysis, battery_percent)
                        else:
                            # Ending a high power event - record it
                            if (
                                self.high_power_event_start is not None
                                and self.high_power_event_data
                            ):
                                duration_seconds = int(time.time() - self.high_power_event_start)

                                # Calculate average power draw during event
                                avg_power_draw = sum(self.high_power_event_data) / len(
                                    self.high_power_event_data
                                )

                                # Get analysis for cause determination
                                analysis = self.analyzer.analyze_current_state(metrics)
                                primary_cause = analysis.get("primary_cause", "UNKNOWN")

                                # Get processes involved
                                processes = []
                                if "causes" in analysis and analysis["causes"]:
                                    for cause in analysis["causes"][:3]:  # Top 3 causes
                                        if "processes" in cause and cause["processes"]:
                                            processes.extend(cause["processes"])

                                processes_involved = ", ".join(
                                    set(processes[:5])
                                )  # Top 5 unique processes

                                # Insert event into database
                                event = {
                                    "timestamp": int(self.high_power_event_start),
                                    "duration_seconds": duration_seconds,
                                    "primary_cause": primary_cause,
                                    "processes_involved": processes_involved,
                                    "avg_power_draw": avg_power_draw,
                                }

                                try:
                                    self.database.insert_high_power_event(event)
                                    self.logger.info(
                                        f"Recorded high power event: duration={duration_seconds}s, "
                                        f"cause={primary_cause}, avg_draw={avg_power_draw:.2f}%/hr"
                                    )
                                except Exception as e:
                                    self.logger.error(
                                        f"Failed to insert high power event: {e}", exc_info=True
                                    )

                                # Reset tracking
                                self.high_power_event_start = None
                                self.high_power_event_data = []

                    # If currently in high power state, track the data
                    if is_high and power_draw is not None:
                        self.high_power_event_data.append(power_draw)

                    # Check for low/critical battery
                    battery_percent = metrics.get("battery_percent")
                    power_plugged = metrics.get("power_plugged", 1)

                    if battery_percent is not None and not power_plugged:
                        critical_threshold = self.config.get("critical_battery_percent", 10)
                        low_threshold = self.config.get("low_battery_warning_percent", 20)

                        if battery_percent <= critical_threshold:
                            if self.config.get("enable_notifications", True):
                                self.notifier.notify_critical_battery(battery_percent)
                        elif battery_percent <= low_threshold:
                            if self.config.get("enable_notifications", True):
                                self.notifier.notify_low_battery(battery_percent)

            except Exception as e:
                self.logger.error(f"Error in high power check: {e}", exc_info=True)

            # Wait for next check interval
            interval = self.config.get("monitoring_interval_seconds", 30)
            self.shutdown_event.wait(timeout=interval)

    def start_monitoring(self):
        """Start the monitoring thread if not already running."""
        if self.monitor.running.is_set():
            self.logger.info("Monitoring already running")
            return

        self.logger.info("Starting monitoring...")
        self.monitor.start()

        # Start analysis thread if not running
        if self.analysis_thread is None or not self.analysis_thread.is_alive():
            self.analysis_thread = threading.Thread(target=self._check_high_power_draw, daemon=True)
            self.analysis_thread.start()

        self.logger.info("Monitoring started")

    def stop_monitoring(self):
        """Stop the monitoring thread."""
        if not self.monitor.running.is_set():
            self.logger.info("Monitoring not running")
            return

        self.logger.info("Stopping monitoring...")
        self.monitor.stop()
        self.logger.info("Monitoring stopped")

    def _on_current_stats(self, icon, item):
        """Handle 'Current Stats' menu click."""
        self.logger.debug("Opening Current Stats window")
        try:
            StatsWindow(self.root, self.monitor)
        except Exception as e:
            self.logger.error(f"Error opening stats window: {e}", exc_info=True)
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to open stats window:\n{str(e)}"))

    def _on_view_power_curve(self, icon, item):
        """Handle 'View Power Curve' menu click."""
        self.logger.debug("Opening Power Curve window")
        try:
            PlotWindow(self.root, self.plotter)
        except Exception as e:
            self.logger.error(f"Error opening plot window: {e}", exc_info=True)
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to open plot window:\n{str(e)}"))

    def _on_settings(self, icon, item):
        """Handle 'Settings' menu click."""
        self.logger.debug("Opening Settings window")
        try:
            SettingsWindow(self.root, self.config, on_save_callback=self._on_settings_saved)
        except Exception as e:
            self.logger.error(f"Error opening settings window: {e}", exc_info=True)
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to open settings window:\n{str(e)}"))

    def _on_settings_saved(self):
        """Callback when settings are saved."""
        self.logger.info("Settings saved, applying changes...")

        # Restart monitoring if it was running to apply new interval
        if self.monitor.running.is_set():
            self.logger.info("Restarting monitoring to apply new settings")
            self.stop_monitoring()
            self.start_monitoring()

    def _on_open_logs_folder(self, icon, item):
        """Handle 'Open Logs Folder' menu click."""
        self.logger.debug("Opening logs folder")
        try:
            logs_path = Path("data/logs").resolve()

            # Create folder if it doesn't exist
            logs_path.mkdir(parents=True, exist_ok=True)

            # Determine file explorer command based on OS
            system = platform.system().lower()

            if system == "windows":
                os.startfile(logs_path)
            elif system == "darwin":  # macOS
                subprocess.Popen(["open", str(logs_path)])
            else:  # Linux and others
                subprocess.Popen(["xdg-open", str(logs_path)])

            self.logger.info(f"Opened logs folder: {logs_path}")

        except Exception as e:
            self.logger.error(f"Error opening logs folder: {e}", exc_info=True)
            messagebox.showerror("Error", f"Failed to open logs folder:\n{str(e)}")

    def _on_about(self, icon, item):
        """Handle 'About' menu click."""
        self.logger.debug("Showing About dialog")
        try:
            about_text = (
                "Power Monitor\n\n"
                "Version 1.0.0\n\n"
                "A battery power draw monitoring application\n"
                "that tracks system resource usage and alerts\n"
                "you to high power consumption.\n\n"
                "Features:\n"
                "- Real-time battery monitoring\n"
                "- Power draw analysis\n"
                "- System resource tracking\n"
                "- Visual power usage graphs\n"
                "- Configurable alerts\n\n"
                "Platform: " + platform.system() + "\n"
                "Python: " + platform.python_version()
            )

            self.root.after(0, lambda: messagebox.showinfo("About Power Monitor", about_text))

        except Exception as e:
            self.logger.error(f"Error showing about dialog: {e}", exc_info=True)

    def _on_quit(self, icon, item):
        """Handle 'Quit' menu click."""
        self.logger.info("Quit requested from tray menu")
        self.shutdown()

    def shutdown(self):
        """Perform graceful shutdown of the application."""
        self.logger.info("Initiating shutdown...")

        # Set shutdown event
        self.shutdown_event.set()

        # Stop monitoring
        if self.monitor.running.is_set():
            self.monitor.stop()

        # Close database
        self.database.close()

        # Stop system tray icon
        if self.icon:
            self.icon.stop()

        # Destroy root window
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass

        self.logger.info("Shutdown complete")

    def _create_tray_menu(self):
        """
        Create system tray menu.

        Returns:
            pystray.Menu object
        """
        return pystray.Menu(
            pystray.MenuItem("Current Stats", self._on_current_stats),
            pystray.MenuItem("View Power Curve", self._on_view_power_curve),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings", self._on_settings),
            pystray.MenuItem("Open Logs Folder", self._on_open_logs_folder),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("About", self._on_about),
            pystray.MenuItem("Quit", self._on_quit),
        )

    def run(self):
        """Run the application with system tray icon."""
        try:
            # Load icon image
            icon_image = self._load_icon_image(self.icon_normal_path)

            if icon_image is None:
                self.logger.error("Failed to load icon image, cannot start")
                return

            # Create system tray icon
            self.icon = pystray.Icon(
                "Power Monitor", icon_image, "Power Monitor", menu=self._create_tray_menu()
            )

            # Auto-start monitoring if configured
            if self.config.get("auto_start_monitoring", True):
                self.logger.info("Auto-starting monitoring")
                self.start_monitoring()

            self.logger.info("Starting system tray icon...")

            # Run icon (this blocks until icon.stop() is called)
            self.icon.run()

        except Exception as e:
            self.logger.error(f"Error running application: {e}", exc_info=True)
            raise

        finally:
            # Ensure clean shutdown
            if not self.shutdown_event.is_set():
                self.shutdown()


def main():
    """Entry point for the application."""
    try:
        # Create and run application
        app = PowerMonitorApp()
        app.run()

    except KeyboardInterrupt:
        print("\nShutdown requested by user")

    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
