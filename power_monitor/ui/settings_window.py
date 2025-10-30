"""
Settings window for Power Monitor application.

Provides a tkinter-based UI for configuring all application settings.
"""

import logging
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class SettingsWindow(tk.Toplevel):
    """Settings dialog for configuring Power Monitor application."""

    def __init__(self, parent, config_manager, on_save_callback: Optional[Callable] = None):
        """
        Initialize the settings window.

        Args:
            parent: Parent tkinter window
            config_manager: ConfigManager instance for loading/saving settings
            on_save_callback: Optional callback function to call after successful save
        """
        super().__init__(parent)

        self.config_manager = config_manager
        self.on_save_callback = on_save_callback

        # Window configuration
        self.title("Power Monitor Settings")
        self.geometry("500x600")
        self.resizable(False, False)

        # Make window modal
        self.transient(parent)
        self.grab_set()

        # Center window on parent
        self._center_on_parent(parent)

        # Initialize widget storage
        self.widgets = {}

        # Create UI
        self._create_widgets()

        # Load current configuration
        self._load_current_config()

        logger.debug("Settings window initialized")

    def _center_on_parent(self, parent):
        """Center the window on the parent window."""
        self.update_idletasks()

        # Get parent position and size
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        # Calculate position
        window_width = 500
        window_height = 600
        x = parent_x + (parent_width - window_width) // 2
        y = parent_y + (parent_height - window_height) // 2

        self.geometry(f"{window_width}x{window_height}+{x}+{y}")

    def _create_widgets(self):
        """Create all UI widgets."""
        # Main container with padding
        main_frame = ttk.Frame(self, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        # Create scrollable frame for settings
        canvas = tk.Canvas(main_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Grid layout for canvas and scrollbar
        canvas.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=2, sticky=(tk.N, tk.S))
        main_frame.rowconfigure(0, weight=1)

        row = 0

        # Monitoring Interval
        row = self._add_entry_field(
            scrollable_frame,
            row,
            "Monitoring Interval (seconds):",
            "monitoring_interval_seconds",
            "How often to check battery status (5-300 seconds)",
        )

        # High Power Threshold
        row = self._add_entry_field(
            scrollable_frame,
            row,
            "High Power Threshold (%/10min):",
            "high_power_threshold_percent_per_10min",
            "Battery drain rate that triggers high power warning (0.1-50.0)",
        )

        # Low Battery Warning
        row = self._add_scale_field(
            scrollable_frame,
            row,
            "Low Battery Warning (%):",
            "low_battery_warning_percent",
            from_=5,
            to=50,
            description="Battery percentage that triggers low battery warning",
        )

        # Critical Battery
        row = self._add_scale_field(
            scrollable_frame,
            row,
            "Critical Battery (%):",
            "critical_battery_percent",
            from_=1,
            to=20,
            description="Battery percentage that triggers critical battery warning",
        )

        # Notification Cooldown
        row = self._add_entry_field(
            scrollable_frame,
            row,
            "Notification Cooldown (min):",
            "notification_cooldown_minutes",
            "Minimum time between repeated notifications (1-120 minutes)",
        )

        # Data Retention
        row = self._add_entry_field(
            scrollable_frame,
            row,
            "Data Retention (days):",
            "data_retention_days",
            "How long to keep historical data (1-365 days)",
        )

        # Log Level
        row = self._add_combobox_field(
            scrollable_frame,
            row,
            "Log Level:",
            "log_level",
            values=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            description="Application logging verbosity level",
        )

        # Enable Notifications
        row = self._add_checkbox_field(
            scrollable_frame,
            row,
            "Enable Notifications:",
            "enable_notifications",
            "Show system notifications for battery events",
        )

        # Auto Start Monitoring
        row = self._add_checkbox_field(
            scrollable_frame,
            row,
            "Auto Start Monitoring:",
            "auto_start_monitoring",
            "Automatically start monitoring when application launches",
        )

        # Separator
        separator = ttk.Separator(main_frame, orient="horizontal")
        separator.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)

        # Buttons
        ttk.Button(button_frame, text="Save", command=self._on_save).grid(row=0, column=0, padx=5)

        ttk.Button(button_frame, text="Cancel", command=self._on_cancel).grid(
            row=0, column=1, padx=5
        )

        ttk.Button(button_frame, text="Reset to Defaults", command=self._on_reset).grid(
            row=0, column=2, padx=5
        )

    def _add_entry_field(self, parent, row: int, label: str, key: str, description: str) -> int:
        """
        Add an entry field to the settings form.

        Args:
            parent: Parent widget
            row: Current row number
            label: Label text
            key: Configuration key
            description: Tooltip/description text

        Returns:
            Next row number
        """
        # Label
        lbl = ttk.Label(parent, text=label)
        lbl.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)

        # Entry
        entry = ttk.Entry(parent, width=30)
        entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Description
        desc = ttk.Label(parent, text=description, font=("", 8), foreground="gray")
        desc.grid(row=row + 1, column=1, sticky=tk.W, padx=5, pady=(0, 5))

        # Store widget
        self.widgets[key] = entry

        return row + 2

    def _add_scale_field(
        self, parent, row: int, label: str, key: str, from_: float, to: float, description: str
    ) -> int:
        """
        Add a scale slider field to the settings form.

        Args:
            parent: Parent widget
            row: Current row number
            label: Label text
            key: Configuration key
            from_: Minimum value
            to: Maximum value
            description: Tooltip/description text

        Returns:
            Next row number
        """
        # Label
        lbl = ttk.Label(parent, text=label)
        lbl.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)

        # Frame for scale and value label
        scale_frame = ttk.Frame(parent)
        scale_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Value label
        value_var = tk.DoubleVar()
        value_label = ttk.Label(scale_frame, textvariable=value_var, width=5)
        value_label.grid(row=0, column=1, padx=(5, 0))

        # Scale
        scale = ttk.Scale(
            scale_frame,
            from_=from_,
            to=to,
            orient=tk.HORIZONTAL,
            variable=value_var,
            command=lambda v: value_var.set(round(float(v))),
        )
        scale.grid(row=0, column=0, sticky=(tk.W, tk.E))
        scale_frame.columnconfigure(0, weight=1)

        # Description
        desc = ttk.Label(parent, text=description, font=("", 8), foreground="gray")
        desc.grid(row=row + 1, column=1, sticky=tk.W, padx=5, pady=(0, 5))

        # Store widget (store the variable, not the scale)
        self.widgets[key] = value_var

        return row + 2

    def _add_combobox_field(
        self, parent, row: int, label: str, key: str, values: list, description: str
    ) -> int:
        """
        Add a combobox field to the settings form.

        Args:
            parent: Parent widget
            row: Current row number
            label: Label text
            key: Configuration key
            values: List of valid values
            description: Tooltip/description text

        Returns:
            Next row number
        """
        # Label
        lbl = ttk.Label(parent, text=label)
        lbl.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)

        # Combobox
        combo = ttk.Combobox(parent, values=values, state="readonly", width=28)
        combo.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=5, pady=5)

        # Description
        desc = ttk.Label(parent, text=description, font=("", 8), foreground="gray")
        desc.grid(row=row + 1, column=1, sticky=tk.W, padx=5, pady=(0, 5))

        # Store widget
        self.widgets[key] = combo

        return row + 2

    def _add_checkbox_field(self, parent, row: int, label: str, key: str, description: str) -> int:
        """
        Add a checkbox field to the settings form.

        Args:
            parent: Parent widget
            row: Current row number
            label: Label text
            key: Configuration key
            description: Tooltip/description text

        Returns:
            Next row number
        """
        # Label
        lbl = ttk.Label(parent, text=label)
        lbl.grid(row=row, column=0, sticky=tk.W, padx=5, pady=5)

        # Checkbox
        var = tk.BooleanVar()
        checkbox = ttk.Checkbutton(parent, variable=var)
        checkbox.grid(row=row, column=1, sticky=tk.W, padx=5, pady=5)

        # Description
        desc = ttk.Label(parent, text=description, font=("", 8), foreground="gray")
        desc.grid(row=row + 1, column=1, sticky=tk.W, padx=5, pady=(0, 5))

        # Store widget (store the variable, not the checkbutton)
        self.widgets[key] = var

        return row + 2

    def _load_current_config(self):
        """Load current configuration values into the form."""
        try:
            config = self.config_manager.get_all()

            for key, widget in self.widgets.items():
                value = config.get(key)

                if isinstance(widget, tk.BooleanVar) or isinstance(widget, tk.DoubleVar):
                    widget.set(value)
                elif isinstance(widget, ttk.Entry):
                    widget.delete(0, tk.END)
                    widget.insert(0, str(value))
                elif isinstance(widget, ttk.Combobox):
                    widget.set(value)

            logger.debug("Configuration loaded into settings window")

        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            messagebox.showerror("Error", f"Failed to load configuration: {e}")

    def _validate_inputs(self) -> tuple[bool, Optional[str]]:
        """
        Validate all input fields.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Monitoring Interval
            try:
                interval = float(self.widgets["monitoring_interval_seconds"].get())
                if not (5 <= interval <= 300):
                    return False, "Monitoring interval must be between 5 and 300 seconds"
            except ValueError:
                return False, "Monitoring interval must be a valid number"

            # High Power Threshold
            try:
                threshold = float(self.widgets["high_power_threshold_percent_per_10min"].get())
                if not (0.1 <= threshold <= 50.0):
                    return False, "High power threshold must be between 0.1 and 50.0"
            except ValueError:
                return False, "High power threshold must be a valid number"

            # Low Battery Warning
            low_battery = int(self.widgets["low_battery_warning_percent"].get())
            if not (5 <= low_battery <= 50):
                return False, "Low battery warning must be between 5 and 50 percent"

            # Critical Battery
            critical_battery = int(self.widgets["critical_battery_percent"].get())
            if not (1 <= critical_battery <= 20):
                return False, "Critical battery must be between 1 and 20 percent"

            # Ensure critical is lower than low
            if critical_battery >= low_battery:
                return False, "Critical battery must be lower than low battery warning"

            # Notification Cooldown
            try:
                cooldown = float(self.widgets["notification_cooldown_minutes"].get())
                if not (1 <= cooldown <= 120):
                    return False, "Notification cooldown must be between 1 and 120 minutes"
            except ValueError:
                return False, "Notification cooldown must be a valid number"

            # Data Retention
            try:
                retention = int(self.widgets["data_retention_days"].get())
                if not (1 <= retention <= 365):
                    return False, "Data retention must be between 1 and 365 days"
            except ValueError:
                return False, "Data retention must be a valid integer"

            # Log Level
            log_level = self.widgets["log_level"].get()
            if log_level not in self.config_manager.VALID_LOG_LEVELS:
                return False, f"Invalid log level: {log_level}"

            return True, None

        except Exception as e:
            logger.error(f"Error during validation: {e}")
            return False, f"Validation error: {e}"

    def _collect_values(self) -> dict:
        """
        Collect all values from the form.

        Returns:
            Dictionary of configuration values
        """
        values = {}

        # Entry fields (convert to appropriate types)
        values["monitoring_interval_seconds"] = float(
            self.widgets["monitoring_interval_seconds"].get()
        )
        values["high_power_threshold_percent_per_10min"] = float(
            self.widgets["high_power_threshold_percent_per_10min"].get()
        )
        values["notification_cooldown_minutes"] = float(
            self.widgets["notification_cooldown_minutes"].get()
        )
        values["data_retention_days"] = int(self.widgets["data_retention_days"].get())

        # Scale fields (already numeric)
        values["low_battery_warning_percent"] = int(
            self.widgets["low_battery_warning_percent"].get()
        )
        values["critical_battery_percent"] = int(self.widgets["critical_battery_percent"].get())

        # Combobox fields
        values["log_level"] = self.widgets["log_level"].get()

        # Checkbox fields
        values["enable_notifications"] = self.widgets["enable_notifications"].get()
        values["auto_start_monitoring"] = self.widgets["auto_start_monitoring"].get()

        return values

    def _on_save(self):
        """Handle save button click."""
        try:
            # Validate inputs
            is_valid, error_message = self._validate_inputs()
            if not is_valid:
                messagebox.showerror("Validation Error", error_message)
                logger.warning(f"Validation failed: {error_message}")
                return

            # Collect values
            values = self._collect_values()

            # Update configuration
            if self.config_manager.update(values):
                # Save to file
                if self.config_manager.save():
                    logger.info("Configuration saved successfully")

                    # Call callback if provided
                    if self.on_save_callback:
                        try:
                            self.on_save_callback()
                        except Exception as e:
                            logger.error(f"Error in save callback: {e}")

                    # Show success message
                    messagebox.showinfo("Success", "Settings saved successfully!")

                    # Close window
                    self.destroy()
                else:
                    messagebox.showerror("Error", "Failed to save configuration to file")
            else:
                messagebox.showerror("Error", "Failed to update configuration")

        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            messagebox.showerror("Error", f"An error occurred while saving settings: {e}")

    def _on_cancel(self):
        """Handle cancel button click."""
        logger.debug("Settings window cancelled")
        self.destroy()

    def _on_reset(self):
        """Handle reset to defaults button click."""
        # Confirm with user
        result = messagebox.askyesno(
            "Confirm Reset",
            "Are you sure you want to reset all settings to their default values?\n\n"
            "This action cannot be undone.",
        )

        if result:
            try:
                # Reset configuration
                if self.config_manager.reset_to_defaults():
                    # Reload form with default values
                    self._load_current_config()

                    logger.info("Configuration reset to defaults")
                    messagebox.showinfo(
                        "Success",
                        "Settings have been reset to default values.\n\n"
                        "Click 'Save' to apply these changes.",
                    )
                else:
                    messagebox.showerror("Error", "Failed to reset configuration to defaults")

            except Exception as e:
                logger.error(f"Error resetting settings: {e}")
                messagebox.showerror("Error", f"An error occurred while resetting settings: {e}")
