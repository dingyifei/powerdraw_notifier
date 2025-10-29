"""
Database operations for Power Monitor using SQLite.

Handles all database operations including:
- Creating and managing SQLite database
- Inserting metrics and events
- Querying data for analysis and plotting
- Cleaning up old data
"""

import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd


class PowerDatabase:
    """Thread-safe SQLite database manager for power monitoring data."""

    def __init__(self, db_path: str = "data/power_history.db"):
        """
        Initialize the database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.lock = threading.Lock()

        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database schema
        self._init_db()

    def _init_db(self):
        """Create database tables if they don't exist."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create power metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS power_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    battery_percent REAL,
                    power_plugged INTEGER,
                    power_draw_estimate REAL,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_read_mb REAL,
                    disk_write_mb REAL,
                    network_sent_mb REAL,
                    network_recv_mb REAL,
                    top_process_name TEXT,
                    top_process_cpu REAL
                )
            """)

            # Create index on timestamp for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON power_metrics(timestamp)
            """)

            # Create high power events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS high_power_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    duration_seconds INTEGER,
                    primary_cause TEXT,
                    processes_involved TEXT,
                    avg_power_draw REAL
                )
            """)

            conn.commit()
            conn.close()

    def insert_metrics(self, metrics: Dict) -> bool:
        """
        Insert power metrics into database.

        Args:
            metrics: Dictionary containing metric data

        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO power_metrics (
                        timestamp, battery_percent, power_plugged, power_draw_estimate,
                        cpu_percent, memory_percent, disk_read_mb, disk_write_mb,
                        network_sent_mb, network_recv_mb, top_process_name, top_process_cpu
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.get('timestamp', int(time.time())),
                    metrics.get('battery_percent'),
                    metrics.get('power_plugged'),
                    metrics.get('power_draw_estimate'),
                    metrics.get('cpu_percent'),
                    metrics.get('memory_percent'),
                    metrics.get('disk_read_mb'),
                    metrics.get('disk_write_mb'),
                    metrics.get('network_sent_mb'),
                    metrics.get('network_recv_mb'),
                    metrics.get('top_process_name'),
                    metrics.get('top_process_cpu')
                ))

                conn.commit()
                conn.close()
                return True

            except Exception as e:
                print(f"Error inserting metrics: {e}")
                return False

    def insert_high_power_event(self, event: Dict) -> bool:
        """
        Insert high power event into database.

        Args:
            event: Dictionary containing event data

        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO high_power_events (
                        timestamp, duration_seconds, primary_cause,
                        processes_involved, avg_power_draw
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    event.get('timestamp', int(time.time())),
                    event.get('duration_seconds'),
                    event.get('primary_cause'),
                    event.get('processes_involved'),
                    event.get('avg_power_draw')
                ))

                conn.commit()
                conn.close()
                return True

            except Exception as e:
                print(f"Error inserting high power event: {e}")
                return False

    def get_metrics_range(self, hours: int = 24) -> Optional[pd.DataFrame]:
        """
        Get metrics for the last N hours.

        Args:
            hours: Number of hours to retrieve

        Returns:
            pandas DataFrame with metrics, or None if error
        """
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)

                # Calculate timestamp for N hours ago
                start_time = int(time.time()) - (hours * 3600)

                query = """
                    SELECT * FROM power_metrics
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                """

                df = pd.read_sql_query(query, conn, params=(start_time,))
                conn.close()

                return df

            except Exception as e:
                print(f"Error querying metrics: {e}")
                return None

    def get_latest_metrics(self, count: int = 20) -> List[Dict]:
        """
        Get the most recent N metric records.

        Args:
            count: Number of records to retrieve

        Returns:
            List of dictionaries containing metric data
        """
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT * FROM power_metrics
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (count,))

                rows = cursor.fetchall()
                metrics = [dict(row) for row in rows]

                conn.close()
                return metrics

            except Exception as e:
                print(f"Error getting latest metrics: {e}")
                return []

    def get_rolling_average(self, minutes: int = 10) -> Optional[float]:
        """
        Get average power draw for the last N minutes.

        Args:
            minutes: Time window in minutes

        Returns:
            Average power draw, or None if no data
        """
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                start_time = int(time.time()) - (minutes * 60)

                cursor.execute("""
                    SELECT AVG(power_draw_estimate) as avg_draw
                    FROM power_metrics
                    WHERE timestamp >= ? AND power_draw_estimate IS NOT NULL
                """, (start_time,))

                result = cursor.fetchone()
                conn.close()

                return result[0] if result and result[0] is not None else None

            except Exception as e:
                print(f"Error calculating rolling average: {e}")
                return None

    def get_high_power_events(self, hours: int = 24) -> List[Dict]:
        """
        Get high power events for the last N hours.

        Args:
            hours: Number of hours to retrieve

        Returns:
            List of event dictionaries
        """
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                start_time = int(time.time()) - (hours * 3600)

                cursor.execute("""
                    SELECT * FROM high_power_events
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                """, (start_time,))

                rows = cursor.fetchall()
                events = [dict(row) for row in rows]

                conn.close()
                return events

            except Exception as e:
                print(f"Error getting high power events: {e}")
                return []

    def cleanup_old_records(self, days: int) -> int:
        """
        Delete records older than specified days.

        Args:
            days: Age threshold in days

        Returns:
            Number of records deleted
        """
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Calculate cutoff timestamp
                cutoff_time = int(time.time()) - (days * 24 * 3600)

                # Delete old metrics
                cursor.execute("""
                    DELETE FROM power_metrics
                    WHERE timestamp < ?
                """, (cutoff_time,))

                metrics_deleted = cursor.rowcount

                # Delete old events
                cursor.execute("""
                    DELETE FROM high_power_events
                    WHERE timestamp < ?
                """, (cutoff_time,))

                events_deleted = cursor.rowcount

                conn.commit()

                # Vacuum to reclaim space
                cursor.execute("VACUUM")

                conn.close()

                total_deleted = metrics_deleted + events_deleted
                print(f"Deleted {total_deleted} old records (metrics: {metrics_deleted}, events: {events_deleted})")

                return total_deleted

            except Exception as e:
                print(f"Error cleaning up old records: {e}")
                return 0

    def get_stats(self) -> Dict:
        """
        Get database statistics.

        Returns:
            Dictionary with database stats
        """
        with self.lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # Get metrics count
                cursor.execute("SELECT COUNT(*) FROM power_metrics")
                metrics_count = cursor.fetchone()[0]

                # Get events count
                cursor.execute("SELECT COUNT(*) FROM high_power_events")
                events_count = cursor.fetchone()[0]

                # Get oldest and newest timestamps
                cursor.execute("""
                    SELECT MIN(timestamp), MAX(timestamp)
                    FROM power_metrics
                """)
                oldest, newest = cursor.fetchone()

                # Get database file size
                file_size_mb = self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0

                conn.close()

                return {
                    'metrics_count': metrics_count,
                    'events_count': events_count,
                    'oldest_timestamp': oldest,
                    'newest_timestamp': newest,
                    'file_size_mb': round(file_size_mb, 2)
                }

            except Exception as e:
                print(f"Error getting database stats: {e}")
                return {}

    def close(self):
        """Close database connections (cleanup method)."""
        # SQLite connections are opened/closed per operation
        # This method exists for API consistency
        pass
