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
from power_monitor.syncthing_client import SyncthingClient, SyncthingError

# Import UI components
from power_monitor.ui.plot_window import PlotWindow
from power_monitor.ui.settings_window import SettingsWindow
from power_monitor.ui.stats_window import StatsWindow


# Enable DPI awareness for better display on high DPI monitors
def enable_dpi_awareness():
    """Enable DPI awareness for crisp UI on high DPI displays."""
    try:
        if platform.system() == "Windows":
            # Try to set DPI awareness (Windows 8.1+)
            import ctypes

            try:
                # Try Windows 10 method first (per-monitor DPI awareness v2)
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    # Fallback to Windows 8.1 method (per-monitor DPI awareness v1)
                    ctypes.windll.shcore.SetProcessDpiAwareness(1)
                except Exception:
                    try:
                        # Fallback to Windows Vista/7 method (system DPI awareness)
                        ctypes.windll.user32.SetProcessDPIAware()
                    except Exception:
                        pass  # DPI awareness not available
    except Exception:
        pass  # Silently fail if not supported


# Call before creating any windows
enable_dpi_awareness()


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

        # Initialize Syncthing client if enabled
        self.syncthing_client: Optional[SyncthingClient] = None
        if self.config.get("syncthing_enabled", False):
            api_key = self.config.get("syncthing_api_key", "")
            if api_key:
                try:
                    self.syncthing_client = SyncthingClient(api_key)
                    self.logger.info("Syncthing client initialized")
                except Exception as e:
                    self.logger.error(f"Failed to initialize Syncthing client: {e}", exc_info=True)
            else:
                self.logger.warning("Syncthing enabled but no API key provided")

        # Threading control
        self.shutdown_event = threading.Event()
        self.shutdown_initiated = False  # Prevent double-shutdown
        self.analysis_thread = None
        self.is_high_power_alert = False

        # High power event tracking
        self.high_power_event_start = None
        self.high_power_event_data = []

        # Hidden Tkinter root window (required for dialogs)
        self.root = tk.Tk()
        self.root.withdraw()  # Hide the root window

        # Configure DPI scaling for tkinter
        self._configure_tkinter_scaling()

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
        # Set shutdown event first
        self.shutdown_event.set()
        # Schedule shutdown on Tkinter's event loop to ensure proper cleanup
        try:
            self.root.after_idle(self.shutdown)
        except Exception:
            # If Tkinter is not available, call shutdown directly
            self.shutdown()

    def _check_shutdown_periodic(self):
        """Periodically check if shutdown was requested (makes Ctrl+C responsive)."""
        if self.shutdown_event.is_set():
            self.logger.debug("Shutdown event detected in periodic check")
            self.shutdown()
        else:
            # Check again in 100ms
            self.root.after(100, self._check_shutdown_periodic)

    def _configure_tkinter_scaling(self):
        """Configure tkinter scaling for high DPI displays."""
        try:
            if platform.system() == "Windows":
                import ctypes

                # Get the DPI of the primary monitor
                try:
                    # Windows 8.1+ method
                    user32 = ctypes.windll.user32
                    user32.SetProcessDPIAware()
                    dpi = user32.GetDpiForSystem()
                except Exception:
                    try:
                        # Fallback method
                        hdc = ctypes.windll.user32.GetDC(0)
                        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
                        ctypes.windll.user32.ReleaseDC(0, hdc)
                    except Exception:
                        dpi = 96  # Default DPI

                # Calculate scaling factor (96 DPI is 100% scaling)
                scale_factor = dpi / 96.0

                # Apply scaling to tkinter if not at 100%
                if scale_factor != 1.0:
                    self.root.tk.call("tk", "scaling", scale_factor * 1.33)
                    self.logger.info(
                        f"DPI scaling configured: {dpi} DPI ({scale_factor * 100:.0f}% scaling)"
                    )
                else:
                    self.logger.info("DPI scaling: 96 DPI (100% scaling)")

        except Exception as e:
            self.logger.warning(f"Could not configure DPI scaling: {e}")

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

                        if battery_percent <= critical_threshold and self.config.get(
                            "enable_notifications", True
                        ):
                            self.notifier.notify_critical_battery(battery_percent)
                        elif battery_percent <= low_threshold and self.config.get(
                            "enable_notifications", True
                        ):
                            self.notifier.notify_low_battery(battery_percent)

            except Exception as e:
                self.logger.error(f"Error in high power check: {e}", exc_info=True)

            # Wait for next check interval
            interval = self.config.get("monitoring_interval_seconds", 30)
            self.shutdown_event.wait(timeout=interval)

    def start_monitoring(self):
        """Start the monitoring thread if not already running."""
        if not self.monitor.stop_event.is_set():
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
        if self.monitor.stop_event.is_set():
            self.logger.info("Monitoring not running")
            return

        self.logger.info("Stopping monitoring...")
        self.monitor.stop()
        self.logger.info("Monitoring stopped")

    def _on_current_stats(self, icon, item):
        """Handle 'Current Stats' menu click."""
        self.logger.debug("Opening Current Stats window")
        try:
            # Ensure UI creation happens on main (Tkinter) thread
            self.root.after(0, lambda: StatsWindow(self.root, self.monitor))
        except Exception as e:
            self.logger.error(f"Error opening stats window: {e}", exc_info=True)
            error_msg = str(e)
            self.root.after(
                0,
                lambda: messagebox.showerror("Error", f"Failed to open stats window:\n{error_msg}"),
            )

    def _on_view_power_curve(self, icon, item):
        """Handle 'View Power Curve' menu click."""
        self.logger.debug("Opening Power Curve window")
        try:
            # Ensure UI creation happens on main (Tkinter) thread
            self.root.after(0, lambda: PlotWindow(self.root, self.plotter))
        except Exception as e:
            self.logger.error(f"Error opening plot window: {e}", exc_info=True)
            error_msg = str(e)
            self.root.after(
                0,
                lambda: messagebox.showerror("Error", f"Failed to open plot window:\n{error_msg}"),
            )

    def _get_syncthing_menu_text(self, item):
        """
        Get dynamic menu text for Syncthing based on current state.

        Args:
            item: Menu item (required by pystray)

        Returns:
            Menu text string
        """
        if not self.syncthing_client:
            return "Syncthing: Unknown"

        try:
            status = self.syncthing_client.get_status_text()
            return f"Syncthing: {status}"
        except Exception:
            return "Syncthing: Unknown"

    def _on_toggle_syncthing(self, icon, item):
        """Handle Syncthing pause/resume toggle."""
        self.logger.debug("Toggling Syncthing sync state")

        if not self.syncthing_client:
            self.logger.warning("Syncthing client not initialized")
            self.root.after(
                0,
                lambda: messagebox.showwarning(
                    "Syncthing Not Configured",
                    "Syncthing integration is not properly configured.\n"
                    "Please check your settings.",
                ),
            )
            return

        try:
            # Check current state and toggle
            is_paused = self.syncthing_client.is_paused()

            if is_paused:
                self.syncthing_client.resume_device()
                self.logger.info("Syncthing sync resumed")
                self.root.after(
                    0, lambda: messagebox.showinfo("Syncthing", "Syncthing sync has been resumed.")
                )
            else:
                self.syncthing_client.pause_device()
                self.logger.info("Syncthing sync paused")
                self.root.after(
                    0, lambda: messagebox.showinfo("Syncthing", "Syncthing sync has been paused.")
                )

            # Update menu by recreating it
            if self.icon:
                self.icon.menu = self._create_tray_menu()

        except SyncthingError as e:
            self.logger.error(f"Syncthing error: {e}", exc_info=True)
            error_msg = str(e)
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Syncthing Error", f"Failed to toggle Syncthing:\n\n{error_msg}"
                ),
            )
        except Exception as e:
            self.logger.error(f"Unexpected error toggling Syncthing: {e}", exc_info=True)
            error_msg = str(e)
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Error", f"An unexpected error occurred:\n\n{error_msg}"
                ),
            )

    def _on_settings(self, icon, item):
        """Handle 'Settings' menu click."""
        self.logger.debug("Opening Settings window")
        try:
            # Ensure UI creation happens on main (Tkinter) thread
            self.root.after(
                0,
                lambda: SettingsWindow(
                    self.root, self.config, on_save_callback=self._on_settings_saved
                ),
            )
        except Exception as e:
            self.logger.error(f"Error opening settings window: {e}", exc_info=True)
            error_msg = str(e)
            self.root.after(
                0,
                lambda: messagebox.showerror(
                    "Error", f"Failed to open settings window:\n{error_msg}"
                ),
            )

    def _on_settings_saved(self):
        """Callback when settings are saved."""
        self.logger.info("Settings saved, applying changes...")

        # Reinitialize Syncthing client if settings changed
        if self.config.get("syncthing_enabled", False):
            api_key = self.config.get("syncthing_api_key", "")
            if api_key:
                try:
                    self.syncthing_client = SyncthingClient(api_key)
                    self.logger.info("Syncthing client reinitialized")
                except Exception as e:
                    self.logger.error(
                        f"Failed to reinitialize Syncthing client: {e}", exc_info=True
                    )
                    self.syncthing_client = None
            else:
                self.logger.warning("Syncthing enabled but no API key provided")
                self.syncthing_client = None
        else:
            self.syncthing_client = None
            self.logger.info("Syncthing integration disabled")

        # Update menu to reflect Syncthing changes
        if self.icon:
            self.icon.menu = self._create_tray_menu()

        # Restart monitoring if it was running to apply new interval
        if not self.monitor.stop_event.is_set():
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
        # Prevent double-shutdown
        if self.shutdown_initiated:
            self.logger.debug("Shutdown already in progress, skipping")
            return

        self.shutdown_initiated = True
        self.logger.info("Initiating shutdown...")

        # Set shutdown event
        self.shutdown_event.set()

        # Stop monitoring
        if not self.monitor.stop_event.is_set():
            self.monitor.stop()

        # Close database
        self.database.close()

        # Stop system tray icon
        if self.icon:
            self.icon.stop()

        # Destroy root window - use after() to ensure it runs on main thread
        try:
            # Check if we're on the main thread
            if threading.current_thread() is threading.main_thread():
                # We're on main thread, safe to quit directly
                self.root.quit()
            else:
                # We're on a background thread, schedule quit on main thread
                self.root.after(0, self.root.quit)
        except Exception as e:
            self.logger.error(f"Error quitting Tkinter: {e}")

        self.logger.info("Shutdown complete")

    def _create_tray_menu(self):
        """
        Create system tray menu.

        Returns:
            pystray.Menu object
        """
        menu_items = [
            pystray.MenuItem("Current Stats", self._on_current_stats),
            pystray.MenuItem("View Power Curve", self._on_view_power_curve),
        ]

        # Add Syncthing menu item if enabled
        if self.config.get("syncthing_enabled", False) and self.syncthing_client:
            menu_items.append(pystray.Menu.SEPARATOR)
            menu_items.append(
                pystray.MenuItem(self._get_syncthing_menu_text, self._on_toggle_syncthing)
            )

        menu_items.extend(
            [
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Settings", self._on_settings),
                pystray.MenuItem("Open Logs Folder", self._on_open_logs_folder),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("About", self._on_about),
                pystray.MenuItem("Quit", self._on_quit),
            ]
        )

        return pystray.Menu(*menu_items)

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

            # Platform-specific threading model
            system = platform.system()

            if system in ["Windows", "Linux"]:
                # On Windows/Linux: run pystray in background thread, Tkinter on main thread
                self.logger.info(
                    f"Running on {system}: pystray in background, Tkinter on main thread"
                )
                icon_thread = threading.Thread(
                    target=self.icon.run, daemon=True, name="PystrayThread"
                )
                icon_thread.start()

                # Start periodic shutdown check (makes Ctrl+C responsive)
                self.root.after(100, self._check_shutdown_periodic)

                # Run Tkinter mainloop on main thread (this blocks)
                self.root.mainloop()

            else:  # macOS
                # On macOS: pystray must run on main thread
                self.logger.info("Running on macOS: pystray on main thread")
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
