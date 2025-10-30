"""
Stats window for displaying current system statistics.

Displays real-time system metrics in a tkinter window including battery status,
power draw, CPU usage, memory usage, top process, network I/O, and disk I/O.
"""

import logging
import tkinter as tk
from tkinter import ttk


class StatsWindow(tk.Toplevel):
    """
    Display current system statistics in a tkinter window.

    Shows real-time metrics with auto-refresh every 5 seconds.
    """

    def __init__(self, parent, monitor):
        """
        Initialize the stats window.

        Args:
            parent: Parent tkinter window
            monitor: PowerMonitor instance
        """
        super().__init__(parent)

        self.monitor = monitor
        self.logger = logging.getLogger("PowerMonitor.StatsWindow")
        self.refresh_job = None

        # Configure window
        self.title("System Statistics")
        self.geometry("400x400")
        self.resizable(False, False)

        # Center on parent
        self._center_on_parent(parent)

        # Setup UI
        self._setup_ui()

        # Start refresh cycle
        self._refresh_stats()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _center_on_parent(self, parent):
        """Center this window on the parent window."""
        self.update_idletasks()

        # Get parent position and size
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        # Get this window size
        window_width = 400
        window_height = 400

        # Calculate center position
        x = parent_x + (parent_width - window_width) // 2
        y = parent_y + (parent_height - window_height) // 2

        # Set position
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def _setup_ui(self):
        """Setup the user interface."""
        # Main frame with padding
        main_frame = ttk.Frame(self, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Font styles
        label_font = ("Arial", 10, "bold")
        value_font = ("Arial", 10)

        # Create label-value pairs
        row = 0

        # Battery
        ttk.Label(main_frame, text="Battery:", font=label_font).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.battery_label = ttk.Label(main_frame, text="N/A", font=value_font)
        self.battery_label.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        row += 1

        # Power Draw
        ttk.Label(main_frame, text="Power Draw:", font=label_font).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.power_draw_label = ttk.Label(main_frame, text="N/A", font=value_font)
        self.power_draw_label.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        row += 1

        # CPU Usage
        ttk.Label(main_frame, text="CPU Usage:", font=label_font).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.cpu_label = ttk.Label(main_frame, text="N/A", font=value_font)
        self.cpu_label.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        row += 1

        # Memory Usage
        ttk.Label(main_frame, text="Memory Usage:", font=label_font).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.memory_label = ttk.Label(main_frame, text="N/A", font=value_font)
        self.memory_label.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        row += 1

        # Top Process
        ttk.Label(main_frame, text="Top Process:", font=label_font).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.top_process_label = ttk.Label(main_frame, text="N/A", font=value_font)
        self.top_process_label.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        row += 1

        # Network
        ttk.Label(main_frame, text="Network:", font=label_font).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.network_label = ttk.Label(main_frame, text="N/A", font=value_font)
        self.network_label.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        row += 1

        # Disk
        ttk.Label(main_frame, text="Disk:", font=label_font).grid(
            row=row, column=0, sticky=tk.W, pady=5
        )
        self.disk_label = ttk.Label(main_frame, text="N/A", font=value_font)
        self.disk_label.grid(row=row, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        row += 1

        # Add some spacing
        ttk.Separator(main_frame, orient="horizontal").grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=15
        )
        row += 1

        # Last updated label
        self.last_updated_label = ttk.Label(
            main_frame, text="Last updated: Never", font=("Arial", 8, "italic")
        )
        self.last_updated_label.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        row += 1

        # Close button
        close_button = ttk.Button(main_frame, text="Close", command=self._on_close)
        close_button.grid(row=row, column=0, columnspan=2, pady=(10, 0))

    def _refresh_stats(self):
        """Refresh statistics display."""
        try:
            # Get current stats from monitor
            stats = self.monitor.get_current_stats()

            if stats is None:
                self._display_no_data()
                return

            # Update battery display
            battery_percent = stats.get("battery_percent")
            power_plugged = stats.get("power_plugged")

            if battery_percent is not None:
                status = "Plugged In" if power_plugged else "On Battery"
                self.battery_label.config(text=f"{battery_percent}% ({status})")
            else:
                self.battery_label.config(text="No battery")

            # Update power draw
            power_draw = stats.get("power_draw_estimate")
            if power_draw is not None:
                self.power_draw_label.config(text=f"{power_draw}% per hour")
            else:
                self.power_draw_label.config(text="No data")

            # Update CPU usage
            cpu_percent = stats.get("cpu_percent")
            if cpu_percent is not None:
                self.cpu_label.config(text=f"{cpu_percent}%")
            else:
                self.cpu_label.config(text="N/A")

            # Update memory usage
            memory_percent = stats.get("memory_percent")
            if memory_percent is not None:
                self.memory_label.config(text=f"{memory_percent}%")
            else:
                self.memory_label.config(text="N/A")

            # Update top process
            top_process_name = stats.get("top_process_name")
            top_process_cpu = stats.get("top_process_cpu")

            if top_process_name and top_process_cpu is not None:
                self.top_process_label.config(text=f"{top_process_name} ({top_process_cpu}% CPU)")
            else:
                self.top_process_label.config(text="N/A")

            # Update network
            network_sent = stats.get("network_sent_mb")
            network_recv = stats.get("network_recv_mb")

            if network_sent is not None and network_recv is not None:
                self.network_label.config(text=f"{network_sent} MB/s up, {network_recv} MB/s down")
            else:
                self.network_label.config(text="N/A")

            # Update disk
            disk_read = stats.get("disk_read_mb")
            disk_write = stats.get("disk_write_mb")

            if disk_read is not None and disk_write is not None:
                self.disk_label.config(text=f"{disk_read} MB/s read, {disk_write} MB/s write")
            else:
                self.disk_label.config(text="N/A")

            # Update last updated timestamp
            import datetime

            now = datetime.datetime.now().strftime("%H:%M:%S")
            self.last_updated_label.config(text=f"Last updated: {now}")

        except Exception as e:
            self.logger.error(f"Error refreshing stats: {e}", exc_info=True)
            self._display_error()

        finally:
            # Schedule next refresh (5 seconds)
            self.refresh_job = self.after(5000, self._refresh_stats)

    def _display_no_data(self):
        """Display 'No data' in all fields."""
        self.battery_label.config(text="No data")
        self.power_draw_label.config(text="No data")
        self.cpu_label.config(text="No data")
        self.memory_label.config(text="No data")
        self.top_process_label.config(text="No data")
        self.network_label.config(text="No data")
        self.disk_label.config(text="No data")

        import datetime

        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.last_updated_label.config(text=f"Last updated: {now} (No data)")

    def _display_error(self):
        """Display error state."""
        self.battery_label.config(text="Error")
        self.power_draw_label.config(text="Error")
        self.cpu_label.config(text="Error")
        self.memory_label.config(text="Error")
        self.top_process_label.config(text="Error")
        self.network_label.config(text="Error")
        self.disk_label.config(text="Error")

        import datetime

        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.last_updated_label.config(text=f"Last updated: {now} (Error)")

    def _on_close(self):
        """Handle window close event."""
        # Cancel pending refresh
        if self.refresh_job:
            self.after_cancel(self.refresh_job)
            self.refresh_job = None

        # Destroy window
        self.destroy()
