"""
Power usage analyzer for identifying high power draw causes.

Analyzes collected metrics to determine if power consumption is abnormally high
and identifies the root causes of elevated power draw.
"""

import logging
from typing import Dict, List, Optional


class PowerAnalyzer:
    """
    Analyzes power consumption metrics to identify high power draw causes.

    Examines CPU usage, disk I/O, network activity, and process behavior
    to determine what's causing elevated power consumption.
    """

    # Cause type constants
    HIGH_CPU = "HIGH_CPU"
    HIGH_DISK_IO = "HIGH_DISK_IO"
    HIGH_NETWORK = "HIGH_NETWORK"
    MULTIPLE_PROCESSES = "MULTIPLE_PROCESSES"
    BACKGROUND_ACTIVITY = "BACKGROUND_ACTIVITY"
    UNKNOWN = "UNKNOWN"

    # Thresholds for cause identification
    CPU_HIGH_THRESHOLD = 50.0  # Total CPU percentage
    CPU_SINGLE_PROCESS_THRESHOLD = 25.0  # Single process CPU percentage
    DISK_IO_THRESHOLD = 50.0  # Combined read+write MB/s
    NETWORK_IO_THRESHOLD = 10.0  # Combined sent+received MB/s
    MULTIPLE_PROCESS_MIN_COUNT = 3  # Minimum processes for MULTIPLE_PROCESSES
    MULTIPLE_PROCESS_CPU_MIN = 10.0  # Minimum CPU per process
    MULTIPLE_PROCESS_CPU_MAX = 20.0  # Maximum CPU per process

    def __init__(self, config, database):
        """
        Initialize power analyzer.

        Args:
            config: ConfigManager instance
            database: PowerDatabase instance
        """
        self.config = config
        self.database = database
        self.logger = logging.getLogger("PowerMonitor.Analyzer")

    def analyze_current_state(self, metrics: Dict) -> Dict:
        """
        Analyze current metrics and return comprehensive analysis.

        Args:
            metrics: Dictionary containing current system metrics

        Returns:
            Dictionary containing analysis results with keys:
                - is_high_power: bool
                - primary_cause: str
                - contributing_factors: list
                - top_processes: list
                - confidence: int (0-100)
                - power_draw: float
                - recommendations: str
        """
        try:
            if not metrics:
                self.logger.warning("No metrics provided for analysis")
                return self._empty_analysis()

            # Get power draw
            power_draw = metrics.get("power_draw_estimate", 0.0)

            # Check if power draw is high
            is_high = self.is_high_power_draw(power_draw)

            # Identify causes
            causes = self.identify_causes(metrics)

            # Determine primary cause and contributing factors
            primary_cause = causes[0] if causes else self.UNKNOWN
            contributing_factors = causes[1:] if len(causes) > 1 else []

            # Get top processes (if available in metrics)
            top_processes = self._extract_top_processes(metrics)

            # Calculate confidence level
            confidence = self._calculate_confidence(metrics, causes, power_draw)

            # Generate recommendations
            recommendations = self._generate_recommendations(
                primary_cause, contributing_factors, metrics
            )

            analysis = {
                "is_high_power": is_high,
                "primary_cause": primary_cause,
                "contributing_factors": contributing_factors,
                "top_processes": top_processes,
                "confidence": confidence,
                "power_draw": round(power_draw, 2),
                "recommendations": recommendations,
            }

            self.logger.debug(
                f"Analysis complete: High power={is_high}, "
                f"Primary cause={primary_cause}, "
                f"Confidence={confidence}%"
            )

            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing current state: {e}", exc_info=True)
            return self._empty_analysis()

    def get_rolling_average(self, minutes: int = 10) -> Optional[float]:
        """
        Get average power draw from database for specified time window.

        Args:
            minutes: Time window in minutes (default: 10)

        Returns:
            Average power draw in percent per hour, or None if no data
        """
        try:
            # Validate input
            if minutes <= 0:
                self.logger.warning(f"Invalid minutes value: {minutes}, using default 10")
                minutes = 10

            avg_draw = self.database.get_rolling_average(minutes)

            if avg_draw is not None:
                self.logger.debug(f"Rolling average ({minutes}min): {avg_draw:.2f}%/hr")
                return round(avg_draw, 3)
            self.logger.debug(f"No data available for {minutes} minute rolling average")
            return None

        except Exception as e:
            self.logger.error(f"Error getting rolling average: {e}", exc_info=True)
            return None

    def is_high_power_draw(self, current_draw: float) -> bool:
        """
        Check if current power draw exceeds threshold from config.

        Args:
            current_draw: Current power draw in percent per hour

        Returns:
            True if power draw exceeds threshold, False otherwise
        """
        try:
            # Get threshold from config (percent per 10 minutes)
            threshold_per_10min = self.config.get("high_power_threshold_percent_per_10min", 2.0)

            # Convert to percent per hour for comparison
            threshold_per_hour = threshold_per_10min * 6.0

            # Check if current draw exceeds threshold
            is_high = current_draw > threshold_per_hour

            if is_high:
                self.logger.info(
                    f"High power draw detected: {current_draw:.2f}%/hr "
                    f"(threshold: {threshold_per_hour:.2f}%/hr)"
                )

            return is_high

        except Exception as e:
            self.logger.error(f"Error checking power draw threshold: {e}", exc_info=True)
            return False

    def identify_causes(self, metrics: Dict) -> List[str]:
        """
        Identify and rank causes of high power consumption.

        Analyzes metrics to determine what's causing elevated power draw.
        Returns causes in order of significance.

        Args:
            metrics: Dictionary containing system metrics

        Returns:
            List of cause identifiers, ranked by significance
        """
        try:
            if not metrics:
                return [self.UNKNOWN]

            causes = []

            # Check for high CPU usage
            if self._is_high_cpu(metrics):
                causes.append((self.HIGH_CPU, self._score_cpu(metrics)))

            # Check for high disk I/O
            if self._is_high_disk_io(metrics):
                causes.append((self.HIGH_DISK_IO, self._score_disk_io(metrics)))

            # Check for high network activity
            if self._is_high_network(metrics):
                causes.append((self.HIGH_NETWORK, self._score_network(metrics)))

            # Check for multiple active processes
            if self._is_multiple_processes(metrics):
                causes.append((self.MULTIPLE_PROCESSES, self._score_multiple_processes(metrics)))

            # Sort by score (descending)
            causes.sort(key=lambda x: x[1], reverse=True)

            # Extract just the cause names
            ranked_causes = [cause[0] for cause in causes]

            # If no specific cause identified, mark as unknown
            if not ranked_causes:
                ranked_causes = [self.UNKNOWN]

            self.logger.debug(f"Identified causes: {ranked_causes}")

            return ranked_causes

        except Exception as e:
            self.logger.error(f"Error identifying causes: {e}", exc_info=True)
            return [self.UNKNOWN]

    def _is_high_cpu(self, metrics: Dict) -> bool:
        """Check if CPU usage indicates high power consumption."""
        cpu_percent = metrics.get("cpu_percent", 0.0)
        top_process_cpu = metrics.get("top_process_cpu", 0.0)

        # High if total CPU > 50% OR any single process > 25%
        return (
            cpu_percent > self.CPU_HIGH_THRESHOLD
            or top_process_cpu > self.CPU_SINGLE_PROCESS_THRESHOLD
        )

    def _is_high_disk_io(self, metrics: Dict) -> bool:
        """Check if disk I/O indicates high power consumption."""
        disk_read = metrics.get("disk_read_mb", 0.0)
        disk_write = metrics.get("disk_write_mb", 0.0)

        # High if combined I/O > 50 MB/s
        total_io = disk_read + disk_write
        return total_io > self.DISK_IO_THRESHOLD

    def _is_high_network(self, metrics: Dict) -> bool:
        """Check if network activity indicates high power consumption."""
        net_sent = metrics.get("network_sent_mb", 0.0)
        net_recv = metrics.get("network_recv_mb", 0.0)

        # High if combined network > 10 MB/s
        total_network = net_sent + net_recv
        return total_network > self.NETWORK_IO_THRESHOLD

    def _is_multiple_processes(self, metrics: Dict) -> bool:
        """Check if multiple processes are consuming moderate CPU."""
        # This is a heuristic check - in a real implementation,
        # we'd need process list data to make this determination
        cpu_percent = metrics.get("cpu_percent", 0.0)
        top_process_cpu = metrics.get("top_process_cpu", 0.0)

        # If total CPU is moderate but no single process dominates,
        # likely multiple processes
        if (
            self.MULTIPLE_PROCESS_CPU_MIN < cpu_percent < self.CPU_HIGH_THRESHOLD
            and top_process_cpu < self.CPU_SINGLE_PROCESS_THRESHOLD
        ):
            return True

        return False

    def _score_cpu(self, metrics: Dict) -> float:
        """Calculate severity score for CPU usage."""
        cpu_percent = metrics.get("cpu_percent", 0.0)
        top_process_cpu = metrics.get("top_process_cpu", 0.0)

        # Score based on how far above threshold
        total_score = max(0, cpu_percent - self.CPU_HIGH_THRESHOLD)
        process_score = max(0, top_process_cpu - self.CPU_SINGLE_PROCESS_THRESHOLD) * 2

        return total_score + process_score

    def _score_disk_io(self, metrics: Dict) -> float:
        """Calculate severity score for disk I/O."""
        disk_read = metrics.get("disk_read_mb", 0.0)
        disk_write = metrics.get("disk_write_mb", 0.0)

        total_io = disk_read + disk_write
        return max(0, total_io - self.DISK_IO_THRESHOLD)

    def _score_network(self, metrics: Dict) -> float:
        """Calculate severity score for network activity."""
        net_sent = metrics.get("network_sent_mb", 0.0)
        net_recv = metrics.get("network_recv_mb", 0.0)

        total_network = net_sent + net_recv
        return max(0, total_network - self.NETWORK_IO_THRESHOLD) * 2

    def _score_multiple_processes(self, metrics: Dict) -> float:
        """Calculate severity score for multiple processes."""
        cpu_percent = metrics.get("cpu_percent", 0.0)

        # Lower score since this is less impactful
        return cpu_percent * 0.5

    def _extract_top_processes(self, metrics: Dict) -> List[Dict]:
        """Extract top process information from metrics."""
        top_processes = []

        # Extract single top process from metrics
        if "top_process_name" in metrics and "top_process_cpu" in metrics:
            top_processes.append(
                {"name": metrics["top_process_name"], "cpu_percent": metrics["top_process_cpu"]}
            )

        return top_processes

    def _calculate_confidence(self, metrics: Dict, causes: List[str], power_draw: float) -> int:
        """
        Calculate confidence level (0-100) for the analysis.

        Higher confidence when:
        - Clear cause identified
        - Power draw is significantly high
        - Metrics are complete
        """
        confidence = 50  # Base confidence

        # Increase confidence if clear causes identified
        if causes and causes[0] != self.UNKNOWN:
            confidence += 20

        # Increase confidence if power draw is very high
        threshold = self.config.get("high_power_threshold_percent_per_10min", 2.0) * 6.0
        if power_draw > threshold * 1.5:
            confidence += 15

        # Increase confidence if we have complete metrics
        required_metrics = ["cpu_percent", "power_draw_estimate"]
        if all(key in metrics for key in required_metrics):
            confidence += 10

        # Increase confidence if top process identified
        if "top_process_name" in metrics:
            confidence += 5

        # Cap at 100
        return min(100, confidence)

    def _generate_recommendations(
        self, primary_cause: str, contributing_factors: List[str], metrics: Dict
    ) -> str:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        # Recommendations based on primary cause
        if primary_cause == self.HIGH_CPU:
            cpu_percent = metrics.get("cpu_percent", 0)
            recommendations.append(
                f"High CPU usage detected ({cpu_percent:.1f}%). "
                "Consider closing unnecessary applications or background processes."
            )

            if "top_process_name" in metrics:
                process_name = metrics["top_process_name"]
                process_cpu = metrics.get("top_process_cpu", 0)
                recommendations.append(
                    f"Process '{process_name}' is using {process_cpu:.1f}% CPU. "
                    "Check if this process needs to be running."
                )

        elif primary_cause == self.HIGH_DISK_IO:
            disk_read = metrics.get("disk_read_mb", 0)
            disk_write = metrics.get("disk_write_mb", 0)
            total_io = disk_read + disk_write
            recommendations.append(
                f"High disk I/O detected ({total_io:.1f} MB/s). "
                "Check for file transfers, backups, or indexing operations."
            )

        elif primary_cause == self.HIGH_NETWORK:
            net_sent = metrics.get("network_sent_mb", 0)
            net_recv = metrics.get("network_recv_mb", 0)
            total_net = net_sent + net_recv
            recommendations.append(
                f"High network activity detected ({total_net:.1f} MB/s). "
                "Check for downloads, uploads, or streaming services."
            )

        elif primary_cause == self.MULTIPLE_PROCESSES:
            recommendations.append(
                "Multiple processes are active simultaneously. "
                "Consider closing background applications to reduce power consumption."
            )

        else:
            recommendations.append(
                "Power consumption is elevated but no specific cause identified. "
                "Check Task Manager for unusual activity."
            )

        # Add recommendations for contributing factors
        if self.HIGH_DISK_IO in contributing_factors:
            recommendations.append("Also check disk I/O activity.")

        if self.HIGH_NETWORK in contributing_factors:
            recommendations.append("Also check network activity.")

        # General power saving tips
        if metrics.get("battery_percent", 100) < 30:
            recommendations.append(
                "Battery is low. Consider enabling battery saver mode or connecting to power."
            )

        return " ".join(recommendations)

    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure for error cases."""
        return {
            "is_high_power": False,
            "primary_cause": self.UNKNOWN,
            "contributing_factors": [],
            "top_processes": [],
            "confidence": 0,
            "power_draw": 0.0,
            "recommendations": "Unable to analyze current state due to insufficient data.",
        }
