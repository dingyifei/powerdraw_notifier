"""
Power monitoring module using psutil.

Collects system metrics including battery status, CPU usage,
memory usage, disk I/O, network I/O, and process information.
"""

import contextlib
import logging
import threading
import time
from typing import Dict, List, Optional

import psutil


class PowerMonitor:
    """
    Monitors system power usage and resource consumption.

    Uses psutil to collect metrics at regular intervals and estimates
    power draw based on battery percentage changes.
    """

    def __init__(self, config, database):
        """
        Initialize power monitor.

        Args:
            config: ConfigManager instance
            database: PowerDatabase instance
        """
        self.config = config
        self.database = database
        self.logger = logging.getLogger("PowerMonitor.Monitor")

        # Threading control
        self.stop_event = threading.Event()  # Set when stopping to wake thread immediately
        self.monitor_thread = None

        # Previous metrics for rate calculations
        self.previous_metrics = None
        self.previous_time = None

        # I/O baseline
        self.last_disk_io = None
        self.last_net_io = None
        self.last_io_time = None

        # Metrics caching (to avoid redundant system calls)
        self._cached_metrics = None
        self._cache_timestamp = None
        self._cache_lock = threading.Lock()

        # Database size-based cleanup tracking
        self._cleanup_check_counter = 0
        self._cleanup_check_interval = 100  # Check database size every 100 monitoring cycles

        # Initialize CPU measurement (non-blocking mode)
        psutil.cpu_percent(interval=0)

    def start(self):
        """Start monitoring in background thread."""
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.logger.warning("Monitor already running")
            return

        self.logger.info("Starting power monitor...")
        self.stop_event.clear()  # Clear stop event to allow thread to run
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop(self):
        """Stop monitoring gracefully."""
        if self.stop_event.is_set():
            self.logger.warning("Monitor not running")
            return

        self.logger.info("Stopping power monitor...")
        self.stop_event.set()  # Signal thread to stop - wakes immediately

        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)  # Reduced timeout since wake is instant

        self.logger.info("Power monitor stopped")

    def _monitor_loop(self):
        """Main monitoring loop."""
        self.logger.info("Monitor loop started")

        # Initialize baselines
        self._initialize_baselines()

        while not self.stop_event.is_set():
            try:
                # Collect metrics
                metrics = self.collect_metrics()

                if metrics:
                    # Cache metrics for other components to use (avoids redundant psutil calls)
                    with self._cache_lock:
                        self._cached_metrics = metrics.copy()
                        self._cache_timestamp = time.time()

                    # Store in database
                    success = self.database.insert_metrics(metrics)

                    if success:
                        self.logger.debug(
                            f"Metrics collected: Battery={metrics.get('battery_percent')}%, CPU={metrics.get('cpu_percent')}%"
                        )

                        # Periodic database size-based cleanup
                        self._cleanup_check_counter += 1
                        if self._cleanup_check_counter >= self._cleanup_check_interval:
                            self._cleanup_check_counter = 0
                            try:
                                max_size_mb = self.config.get("max_database_size_mb", 100)
                                deleted_count = self.database.cleanup_by_size(max_size_mb)
                                if deleted_count > 0:
                                    self.logger.info(
                                        f"Database size cleanup completed: {deleted_count} records removed"
                                    )
                            except Exception as cleanup_error:
                                self.logger.error(
                                    f"Error during database cleanup: {cleanup_error}", exc_info=True
                                )
                    else:
                        self.logger.error("Failed to store metrics in database")

            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}", exc_info=True)

            # Wait for next interval (wakes immediately if stop_event is set)
            interval = self.config.get("monitoring_interval_seconds", 30)
            self.stop_event.wait(timeout=interval)

        self.logger.info("Monitor loop exited")

    def _initialize_baselines(self):
        """Initialize baseline measurements for rate calculations."""
        try:
            # Initialize I/O baselines
            if hasattr(psutil, "disk_io_counters"):
                self.last_disk_io = psutil.disk_io_counters()

            if hasattr(psutil, "net_io_counters"):
                self.last_net_io = psutil.net_io_counters()

            self.last_io_time = time.time()

            # Initialize process CPU measurements
            for proc in psutil.process_iter():
                with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                    proc.cpu_percent()

            # Wait brief moment for initial CPU measurement
            time.sleep(0.1)

        except Exception as e:
            self.logger.warning(f"Error initializing baselines: {e}")

    def collect_metrics(self) -> Optional[Dict]:
        """
        Collect all system metrics.

        Returns:
            Dictionary containing all metrics, or None if error
        """
        try:
            current_time = time.time()
            metrics = {"timestamp": int(current_time)}

            # Collect battery metrics
            battery_info = self._get_battery_info()
            if battery_info:
                metrics.update(battery_info)

            # Collect CPU usage
            metrics["cpu_percent"] = psutil.cpu_percent(interval=0)

            # Collect memory usage
            mem = psutil.virtual_memory()
            metrics["memory_percent"] = mem.percent

            # Collect disk I/O rates
            disk_rates = self._get_disk_io_rates(current_time)
            if disk_rates:
                metrics.update(disk_rates)

            # Collect network I/O rates
            net_rates = self._get_network_io_rates(current_time)
            if net_rates:
                metrics.update(net_rates)

            # Get top CPU process
            top_process = self._get_top_process()
            if top_process:
                metrics["top_process_name"] = top_process["name"]
                metrics["top_process_cpu"] = top_process["cpu_percent"]

            # Calculate power draw estimate
            if (
                self.previous_metrics
                and "battery_percent" in metrics
                and "battery_percent" in self.previous_metrics
            ):
                power_draw = self._calculate_power_draw(
                    current_time, metrics, self.previous_metrics
                )
                metrics["power_draw_estimate"] = power_draw

            # Store for next calculation
            self.previous_metrics = metrics.copy()
            self.previous_time = current_time

            return metrics

        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}", exc_info=True)
            return None

    def _get_battery_info(self) -> Optional[Dict]:
        """
        Get battery information safely.

        Returns:
            Dictionary with battery metrics, or None if no battery
        """
        try:
            if not hasattr(psutil, "sensors_battery"):
                return None

            battery = psutil.sensors_battery()

            if battery is None:
                # No battery installed
                return None

            return {
                "battery_percent": round(battery.percent, 2),
                "power_plugged": 1 if battery.power_plugged else 0,
            }

        except Exception as e:
            self.logger.warning(f"Error getting battery info: {e}")
            return None

    def _calculate_power_draw(
        self, current_time: float, current_metrics: Dict, previous_metrics: Dict
    ) -> float:
        """
        Calculate power draw estimate based on battery percentage change.

        Args:
            current_time: Current timestamp
            current_metrics: Current metrics
            previous_metrics: Previous metrics

        Returns:
            Power draw estimate in percent per hour
        """
        try:
            # Only calculate if on battery
            if current_metrics.get("power_plugged", 0) == 1:
                return 0.0

            battery_now = current_metrics.get("battery_percent", 0)
            battery_prev = previous_metrics.get("battery_percent", 0)

            time_delta = current_time - (self.previous_time or current_time)

            if time_delta <= 0:
                return 0.0

            # Calculate percentage drop per hour
            battery_change = battery_prev - battery_now
            hours_elapsed = time_delta / 3600.0

            if hours_elapsed > 0:
                power_draw = battery_change / hours_elapsed
                return round(power_draw, 3)

            return 0.0

        except Exception as e:
            self.logger.warning(f"Error calculating power draw: {e}")
            return 0.0

    def _get_disk_io_rates(self, current_time: float) -> Optional[Dict]:
        """
        Calculate disk I/O rates in MB/s.

        Args:
            current_time: Current timestamp

        Returns:
            Dictionary with disk I/O rates
        """
        try:
            if not hasattr(psutil, "disk_io_counters"):
                return None

            current_disk = psutil.disk_io_counters()

            if current_disk is None or self.last_disk_io is None:
                self.last_disk_io = current_disk
                self.last_io_time = current_time
                return {"disk_read_mb": 0.0, "disk_write_mb": 0.0}

            time_delta = current_time - self.last_io_time

            if time_delta <= 0:
                return {"disk_read_mb": 0.0, "disk_write_mb": 0.0}

            # Calculate rates
            read_rate = (
                (current_disk.read_bytes - self.last_disk_io.read_bytes)
                / time_delta
                / (1024 * 1024)
            )
            write_rate = (
                (current_disk.write_bytes - self.last_disk_io.write_bytes)
                / time_delta
                / (1024 * 1024)
            )

            # Update last values
            self.last_disk_io = current_disk
            self.last_io_time = current_time

            return {"disk_read_mb": round(read_rate, 2), "disk_write_mb": round(write_rate, 2)}

        except Exception as e:
            self.logger.warning(f"Error getting disk I/O rates: {e}")
            return None

    def _get_network_io_rates(self, current_time: float) -> Optional[Dict]:
        """
        Calculate network I/O rates in MB/s.

        Args:
            current_time: Current timestamp

        Returns:
            Dictionary with network I/O rates
        """
        try:
            if not hasattr(psutil, "net_io_counters"):
                return None

            current_net = psutil.net_io_counters()

            if current_net is None or self.last_net_io is None:
                self.last_net_io = current_net
                return {"network_sent_mb": 0.0, "network_recv_mb": 0.0}

            time_delta = current_time - self.last_io_time

            if time_delta <= 0:
                return {"network_sent_mb": 0.0, "network_recv_mb": 0.0}

            # Calculate rates
            sent_rate = (
                (current_net.bytes_sent - self.last_net_io.bytes_sent) / time_delta / (1024 * 1024)
            )
            recv_rate = (
                (current_net.bytes_recv - self.last_net_io.bytes_recv) / time_delta / (1024 * 1024)
            )

            # Update last values
            self.last_net_io = current_net

            return {"network_sent_mb": round(sent_rate, 2), "network_recv_mb": round(recv_rate, 2)}

        except Exception as e:
            self.logger.warning(f"Error getting network I/O rates: {e}")
            return None

    def _get_top_process(self) -> Optional[Dict]:
        """
        Get the top CPU-consuming process.

        Returns:
            Dictionary with process information
        """
        try:
            top_proc = None
            max_cpu = 0

            for proc in psutil.process_iter(["name", "cpu_percent"]):
                try:
                    # Use oneshot() context manager to cache process info and reduce syscalls
                    with proc.oneshot():
                        cpu = proc.info.get("cpu_percent", 0)
                        if cpu and cpu > max_cpu:
                            max_cpu = cpu
                            top_proc = proc.info

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if top_proc and max_cpu > 0:
                return {"name": top_proc.get("name", "Unknown"), "cpu_percent": round(max_cpu, 1)}

            return None

        except Exception as e:
            self.logger.warning(f"Error getting top process: {e}")
            return None

    def get_current_stats(self) -> Optional[Dict]:
        """
        Get current system statistics (synchronous).

        Returns:
            Dictionary with current stats
        """
        try:
            return self.collect_metrics()
        except Exception as e:
            self.logger.error(f"Error getting current stats: {e}")
            return None

    def get_cached_stats(self, max_age_seconds: float = 5.0) -> Optional[Dict]:
        """
        Get cached system statistics to avoid redundant psutil calls.

        This method returns metrics from the cache if they're fresh enough,
        avoiding expensive system calls. Falls back to collecting new metrics
        if cache is empty or stale.

        Args:
            max_age_seconds: Maximum age of cached data in seconds (default: 5.0)

        Returns:
            Dictionary with cached or fresh stats
        """
        try:
            with self._cache_lock:
                # Check if cache exists and is fresh
                if self._cached_metrics and self._cache_timestamp:
                    age = time.time() - self._cache_timestamp
                    if age <= max_age_seconds:
                        self.logger.debug(f"Using cached metrics (age: {age:.1f}s)")
                        return self._cached_metrics.copy()

            # Cache is stale or empty, collect new metrics
            self.logger.debug("Cache miss or stale, collecting new metrics")
            return self.collect_metrics()

        except Exception as e:
            self.logger.error(f"Error getting cached stats: {e}")
            return None

    def get_top_processes(self, n: int = 5) -> List[Dict]:
        """
        Get top N CPU-consuming processes.

        Args:
            n: Number of processes to return

        Returns:
            List of process dictionaries
        """
        try:
            # First pass: initialize CPU measurement
            for proc in psutil.process_iter():
                with contextlib.suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                    proc.cpu_percent()

            time.sleep(0.1)

            # Second pass: collect
            processes = []
            for proc in psutil.process_iter(["pid", "name", "cpu_percent"]):
                try:
                    if proc.info["cpu_percent"] and proc.info["cpu_percent"] > 0:
                        processes.append(
                            {
                                "pid": proc.info["pid"],
                                "name": proc.info["name"],
                                "cpu_percent": round(proc.info["cpu_percent"], 1),
                            }
                        )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Sort and return top N
            processes.sort(key=lambda x: x["cpu_percent"], reverse=True)
            return processes[:n]

        except Exception as e:
            self.logger.error(f"Error getting top processes: {e}")
            return []
