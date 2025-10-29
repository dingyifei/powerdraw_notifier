"""
Logging and data persistence management for Power Monitor.

Sets up Python logging with rotating file handlers and manages
data cleanup based on retention policies.
"""

import logging
import time
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logging(config, log_dir: str = "data/logs") -> logging.Logger:
    """
    Configure logging with rotating file handler.

    Args:
        config: ConfigManager instance
        log_dir: Directory for log files

    Returns:
        Configured logger instance
    """
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Get log level from config
    log_level_str = config.get("log_level", "INFO")
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Create logger
    logger = logging.getLogger("PowerMonitor")
    logger.setLevel(log_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # File handler with rotation (10 MB max, keep 5 backups)
    log_file = log_path / f"power_monitor_{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only show warnings and errors in console
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    logger.info("="*60)
    logger.info("Power Monitor logging initialized")
    logger.info(f"Log level: {log_level_str}")
    logger.info(f"Log file: {log_file}")
    logger.info("="*60)

    return logger


def cleanup_old_logs(log_dir: str = "data/logs", retention_days: int = 30) -> int:
    """
    Delete log files older than retention period.

    Args:
        log_dir: Directory containing log files
        retention_days: Age threshold in days

    Returns:
        Number of files deleted
    """
    log_path = Path(log_dir)

    if not log_path.exists():
        return 0

    deleted_count = 0
    cutoff_time = time.time() - (retention_days * 24 * 3600)

    try:
        for log_file in log_path.glob("*.log*"):
            # Check file modification time
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    deleted_count += 1
                    print(f"Deleted old log file: {log_file.name}")
                except Exception as e:
                    print(f"Error deleting log file {log_file}: {e}")

    except Exception as e:
        print(f"Error cleaning up log files: {e}")

    return deleted_count


def cleanup_old_data(database, retention_days: int, log_dir: str = "data/logs") -> dict:
    """
    Clean old data from both database and log files.

    Args:
        database: PowerDatabase instance
        retention_days: Age threshold in days
        log_dir: Directory containing log files

    Returns:
        Dictionary with cleanup statistics
    """
    stats = {
        'db_records_deleted': 0,
        'log_files_deleted': 0,
        'success': False
    }

    try:
        # Clean database records
        stats['db_records_deleted'] = database.cleanup_old_records(retention_days)

        # Clean log files
        stats['log_files_deleted'] = cleanup_old_logs(log_dir, retention_days)

        stats['success'] = True

        print(f"Data cleanup complete:")
        print(f"  - Database records deleted: {stats['db_records_deleted']}")
        print(f"  - Log files deleted: {stats['log_files_deleted']}")

    except Exception as e:
        print(f"Error during data cleanup: {e}")
        stats['error'] = str(e)

    return stats


class LogManager:
    """Manages periodic log cleanup and rotation."""

    def __init__(self, config, database, log_dir: str = "data/logs"):
        """
        Initialize log manager.

        Args:
            config: ConfigManager instance
            database: PowerDatabase instance
            log_dir: Directory for log files
        """
        self.config = config
        self.database = database
        self.log_dir = log_dir
        self.last_cleanup = None

    def should_cleanup(self) -> bool:
        """
        Check if cleanup should be performed.

        Returns:
            True if cleanup is due, False otherwise
        """
        if self.last_cleanup is None:
            return True

        # Cleanup once per day
        time_since_cleanup = time.time() - self.last_cleanup
        return time_since_cleanup >= (24 * 3600)

    def perform_cleanup(self) -> dict:
        """
        Perform data cleanup if needed.

        Returns:
            Dictionary with cleanup statistics, or None if not due
        """
        if not self.should_cleanup():
            return None

        retention_days = self.config.get("data_retention_days", 30)
        stats = cleanup_old_data(self.database, retention_days, self.log_dir)

        if stats['success']:
            self.last_cleanup = time.time()

        return stats

    def get_log_stats(self) -> dict:
        """
        Get statistics about log files.

        Returns:
            Dictionary with log file statistics
        """
        log_path = Path(self.log_dir)

        if not log_path.exists():
            return {
                'log_count': 0,
                'total_size_mb': 0
            }

        log_files = list(log_path.glob("*.log*"))
        total_size = sum(f.stat().st_size for f in log_files if f.is_file())

        return {
            'log_count': len(log_files),
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'oldest_log': min((f.stat().st_mtime for f in log_files), default=None),
            'newest_log': max((f.stat().st_mtime for f in log_files), default=None)
        }
