"""
PowerPlotter - Generate matplotlib figures for power visualization
"""
import logging
import matplotlib
matplotlib.use('Agg')  # Non-GUI backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np

logger = logging.getLogger("PowerMonitor.Plotter")


class PowerPlotter:
    """Generate visualization figures for power monitoring data"""

    def __init__(self, database):
        """
        Initialize the PowerPlotter

        Args:
            database: Database instance for querying metrics
        """
        self.database = database
        logger.info("PowerPlotter initialized")

    def generate_figure(self, hours=24):
        """
        Generate a figure with 3 subplots showing power metrics

        Args:
            hours: Number of hours of historical data to plot (default: 24)

        Returns:
            matplotlib.figure.Figure: The generated figure object
        """
        logger.info(f"Generating figure for {hours} hours of data")

        # Query data from database
        df = self.database.get_metrics_range(hours)

        # Create figure with 3 subplots
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 8), dpi=100)
        fig.suptitle(f'Power Monitor - Last {hours} Hours', fontsize=16, fontweight='bold')

        if df.empty:
            logger.warning("No data available for plotting")
            # Add text to indicate no data
            for ax in [ax1, ax2, ax3]:
                ax.text(0.5, 0.5, 'No data available',
                       horizontalalignment='center',
                       verticalalignment='center',
                       transform=ax.transAxes,
                       fontsize=14, color='gray')
                ax.set_xticks([])
                ax.set_yticks([])

            ax1.set_title('Battery Percentage Over Time')
            ax2.set_title('Power Draw Estimate')
            ax3.set_title('CPU Usage')

            plt.tight_layout()
            return fig

        # Convert timestamps to datetime objects
        timestamps = [datetime.fromtimestamp(ts) for ts in df['timestamp']]

        # Subplot 1: Battery Percentage Over Time
        self._plot_battery_percentage(ax1, timestamps, df)

        # Subplot 2: Power Draw Estimate
        self._plot_power_draw(ax2, timestamps, df)

        # Subplot 3: CPU Usage
        self._plot_cpu_usage(ax3, timestamps, df)

        # Format x-axis for all subplots
        for ax in [ax1, ax2, ax3]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            ax.grid(True, alpha=0.3, linestyle='--')

        plt.tight_layout()
        logger.info("Figure generation complete")
        return fig

    def _plot_battery_percentage(self, ax, timestamps, df):
        """Plot battery percentage with colored zones"""
        ax.set_title('Battery Percentage Over Time', fontweight='bold')
        ax.set_ylabel('Battery %')

        battery_pct = df['battery_percent'].values

        # Plot the main line
        ax.plot(timestamps, battery_pct, color='black', linewidth=2, label='Battery Level')

        # Add colored background zones
        ax.axhspan(0, 20, alpha=0.2, color='red', label='Critical (<20%)')
        ax.axhspan(20, 40, alpha=0.2, color='yellow', label='Warning (20-40%)')
        ax.axhspan(40, 100, alpha=0.2, color='green', label='Good (>40%)')

        ax.set_ylim(0, 100)
        ax.legend(loc='best', fontsize=8)

        logger.debug(f"Battery plot: {len(timestamps)} data points")

    def _plot_power_draw(self, ax, timestamps, df):
        """Plot power draw estimate with shaded regions for high draw"""
        ax.set_title('Power Draw Estimate', fontweight='bold')
        ax.set_ylabel('Power Draw (W)')

        power_draw = df['power_draw_estimate'].values

        # Plot the power draw line
        ax.plot(timestamps, power_draw, color='blue', linewidth=2, label='Power Draw')

        # Determine high power threshold (e.g., 75th percentile or 30W, whichever is higher)
        if len(power_draw) > 0:
            high_threshold = max(np.percentile(power_draw, 75), 30)

            # Shade regions where power draw is high
            ax.fill_between(timestamps, 0, power_draw,
                           where=(power_draw >= high_threshold),
                           alpha=0.3, color='red',
                           label=f'High Draw (≥{high_threshold:.1f}W)')

            # Add horizontal line for threshold
            ax.axhline(y=high_threshold, color='red', linestyle='--',
                      linewidth=1, alpha=0.5)

            # Annotate high power events with vertical lines
            self._annotate_high_power_events(ax, timestamps, power_draw, high_threshold)

        ax.set_ylim(bottom=0)
        ax.legend(loc='best', fontsize=8)

        logger.debug(f"Power draw plot: {len(timestamps)} data points")

    def _annotate_high_power_events(self, ax, timestamps, power_draw, threshold):
        """Add vertical lines for significant high power events"""
        # Find peaks in power draw that exceed threshold
        high_power_indices = []
        in_high_zone = False

        for i, power in enumerate(power_draw):
            if power >= threshold and not in_high_zone:
                # Start of a high power event
                high_power_indices.append(i)
                in_high_zone = True
            elif power < threshold:
                in_high_zone = False

        # Limit annotations to avoid clutter (max 10)
        if len(high_power_indices) > 10:
            # Select the highest peaks
            peak_powers = [(i, power_draw[i]) for i in high_power_indices]
            peak_powers.sort(key=lambda x: x[1], reverse=True)
            high_power_indices = [i for i, _ in peak_powers[:10]]
            high_power_indices.sort()

        # Add vertical lines at high power events
        for idx in high_power_indices:
            ax.axvline(x=timestamps[idx], color='orange',
                      linestyle=':', linewidth=1, alpha=0.6)

        logger.debug(f"Annotated {len(high_power_indices)} high power events")

    def _plot_cpu_usage(self, ax, timestamps, df):
        """Plot CPU usage"""
        ax.set_title('CPU Usage', fontweight='bold')
        ax.set_ylabel('CPU %')
        ax.set_xlabel('Time')

        cpu_usage = df['cpu_percent'].values

        # Plot CPU usage line
        ax.plot(timestamps, cpu_usage, color='purple', linewidth=2, label='CPU Usage')

        # Add reference line at 80% (high usage threshold)
        ax.axhline(y=80, color='red', linestyle='--',
                  linewidth=1, alpha=0.5, label='High Usage (80%)')

        # Shade regions where CPU usage is very high
        ax.fill_between(timestamps, 0, cpu_usage,
                       where=(cpu_usage >= 80),
                       alpha=0.3, color='red')

        ax.set_ylim(0, 100)
        ax.legend(loc='best', fontsize=8)

        logger.debug(f"CPU usage plot: {len(timestamps)} data points")

    def export_png(self, figure, filepath=None):
        """
        Export the figure to a PNG file

        Args:
            figure: matplotlib.figure.Figure object to export
            filepath: Path where the PNG should be saved (default: None)
                     If None, uses a default path with timestamp

        Returns:
            str: Path to the saved PNG file
        """
        if filepath is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f'power_monitor_{timestamp}.png'

        try:
            logger.info(f"Exporting figure to: {filepath}")
            figure.savefig(filepath, dpi=100, bbox_inches='tight')
            logger.info(f"Figure successfully exported to: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to export figure: {e}")
            raise
        finally:
            # Ensure figure is properly closed to free memory
            plt.close(figure)
            logger.debug("Figure closed")
