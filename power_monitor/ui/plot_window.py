"""
PlotWindow - Embed matplotlib plot in tkinter window
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import logging
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import matplotlib.pyplot as plt

logger = logging.getLogger("PowerMonitor.PlotWindow")


class PlotWindow(tk.Toplevel):
    """Toplevel window for displaying interactive matplotlib plots"""

    # Map time range strings to hours
    TIME_RANGE_MAP = {
        "1 hour": 1,
        "6 hours": 6,
        "24 hours": 24,
        "7 days": 168  # 7 * 24 hours
    }

    def __init__(self, parent, plotter):
        """
        Initialize the plot window

        Args:
            parent: Parent tkinter widget
            plotter: PowerPlotter instance for generating figures
        """
        super().__init__(parent)
        self.plotter = plotter
        self.current_figure = None
        self.canvas = None
        self.toolbar = None

        # Configure window
        self.title("Power Monitor - Visualization")
        self.geometry("1000x800")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        logger.info("PlotWindow initialized")

        # Build the UI
        self._create_widgets()

        # Load initial plot
        self._refresh_plot()

    def _create_widgets(self):
        """Create and layout all UI widgets"""

        # Top control frame
        control_frame = ttk.Frame(self, padding="5")
        control_frame.pack(side=tk.TOP, fill=tk.X)

        # Time range label
        ttk.Label(control_frame, text="Time Range:").pack(side=tk.LEFT, padx=(0, 5))

        # Time range selector combobox
        self.time_range_var = tk.StringVar(value="24 hours")
        self.time_range_combo = ttk.Combobox(
            control_frame,
            textvariable=self.time_range_var,
            values=list(self.TIME_RANGE_MAP.keys()),
            state="readonly",
            width=15
        )
        self.time_range_combo.pack(side=tk.LEFT, padx=5)

        # Refresh button
        self.refresh_btn = ttk.Button(
            control_frame,
            text="Refresh",
            command=self._refresh_plot
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=5)

        # Export PNG button
        self.export_btn = ttk.Button(
            control_frame,
            text="Export PNG",
            command=self._export_png
        )
        self.export_btn.pack(side=tk.LEFT, padx=5)

        # Close button
        self.close_btn = ttk.Button(
            control_frame,
            text="Close",
            command=self._on_close
        )
        self.close_btn.pack(side=tk.RIGHT, padx=5)

        # Toolbar frame (will be populated with NavigationToolbar2Tk)
        self.toolbar_frame = ttk.Frame(self)
        self.toolbar_frame.pack(side=tk.TOP, fill=tk.X)

        # Canvas frame for matplotlib figure
        self.canvas_frame = ttk.Frame(self)
        self.canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        logger.debug("Widgets created")

    def _get_selected_hours(self):
        """
        Extract hours from selected time range

        Returns:
            int: Number of hours corresponding to selected time range
        """
        selected = self.time_range_var.get()
        hours = self.TIME_RANGE_MAP.get(selected, 24)  # Default to 24 hours
        logger.debug(f"Selected time range: {selected} -> {hours} hours")
        return hours

    def _refresh_plot(self):
        """Reload data and regenerate the plot"""
        try:
            logger.info("Refreshing plot...")

            # Disable buttons during refresh
            self._set_buttons_state(tk.DISABLED)

            # Get selected time range
            hours = self._get_selected_hours()

            # Generate new figure
            new_figure = self.plotter.generate_figure(hours)

            # Close old figure if exists
            if self.current_figure is not None:
                plt.close(self.current_figure)
                logger.debug("Closed previous figure")

            # Remove old canvas and toolbar if they exist
            if self.canvas is not None:
                self.canvas.get_tk_widget().destroy()
                self.canvas = None

            if self.toolbar is not None:
                self.toolbar.destroy()
                self.toolbar = None

            # Store new figure
            self.current_figure = new_figure

            # Create new canvas with the figure
            self.canvas = FigureCanvasTkAgg(self.current_figure, master=self.canvas_frame)
            self.canvas.draw_idle()  # Thread-safe canvas update
            self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

            # Create new navigation toolbar
            self.toolbar = NavigationToolbar2Tk(self.canvas, self.toolbar_frame)
            self.toolbar.update()

            logger.info("Plot refreshed successfully")

        except Exception as e:
            logger.error(f"Error refreshing plot: {e}", exc_info=True)
            messagebox.showerror(
                "Error",
                f"Failed to refresh plot:\n{str(e)}",
                parent=self
            )

        finally:
            # Re-enable buttons
            self._set_buttons_state(tk.NORMAL)

    def _export_png(self):
        """Export current plot to PNG file"""
        if self.current_figure is None:
            messagebox.showwarning(
                "No Plot",
                "No plot available to export.",
                parent=self
            )
            return

        try:
            # Ask user for file location
            filepath = filedialog.asksaveasfilename(
                parent=self,
                title="Export Plot as PNG",
                defaultextension=".png",
                filetypes=[
                    ("PNG files", "*.png"),
                    ("All files", "*.*")
                ],
                initialfile=f"power_monitor.png"
            )

            if not filepath:
                # User cancelled
                logger.debug("Export cancelled by user")
                return

            logger.info(f"Exporting plot to: {filepath}")

            # Export the figure
            # Note: We need to save without closing, so we'll use savefig directly
            self.current_figure.savefig(filepath, dpi=100, bbox_inches='tight')

            logger.info(f"Plot exported successfully to: {filepath}")
            messagebox.showinfo(
                "Export Successful",
                f"Plot saved to:\n{filepath}",
                parent=self
            )

        except Exception as e:
            logger.error(f"Error exporting plot: {e}", exc_info=True)
            messagebox.showerror(
                "Export Error",
                f"Failed to export plot:\n{str(e)}",
                parent=self
            )

    def _set_buttons_state(self, state):
        """
        Set the state of all control buttons

        Args:
            state: tk.NORMAL or tk.DISABLED
        """
        self.refresh_btn.config(state=state)
        self.export_btn.config(state=state)
        self.close_btn.config(state=state)
        self.time_range_combo.config(state="readonly" if state == tk.NORMAL else "disabled")

    def _on_close(self):
        """Handle window close event - cleanup matplotlib resources"""
        try:
            logger.info("Closing PlotWindow...")

            # Destroy toolbar
            if self.toolbar is not None:
                self.toolbar.destroy()
                self.toolbar = None

            # Destroy canvas
            if self.canvas is not None:
                self.canvas.get_tk_widget().destroy()
                self.canvas = None

            # Close matplotlib figure
            if self.current_figure is not None:
                plt.close(self.current_figure)
                self.current_figure = None
                logger.debug("Matplotlib figure closed")

            # Destroy window
            self.destroy()
            logger.info("PlotWindow closed successfully")

        except Exception as e:
            logger.error(f"Error closing PlotWindow: {e}", exc_info=True)
            # Force destroy even if there's an error
            self.destroy()
