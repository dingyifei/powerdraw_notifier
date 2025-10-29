"""
Configuration management for Power Monitor.

Handles loading, validating, and saving application configuration.
"""

import json
import threading
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """Thread-safe configuration manager."""

    DEFAULT_CONFIG = {
        "monitoring_interval_seconds": 30,
        "high_power_threshold_percent_per_10min": 2.0,
        "low_battery_warning_percent": 20,
        "critical_battery_percent": 10,
        "notification_cooldown_minutes": 15,
        "data_retention_days": 30,
        "log_level": "INFO",
        "enable_notifications": True,
        "auto_start_monitoring": True
    }

    VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def __init__(self, config_path: str = "config.json"):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = Path(config_path)
        self.lock = threading.Lock()
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """
        Load configuration from file, applying defaults if missing.

        Returns:
            Configuration dictionary
        """
        config = self.DEFAULT_CONFIG.copy()

        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)

                # Merge user config with defaults
                config.update(user_config)
                print(f"Configuration loaded from {self.config_path}")

            except json.JSONDecodeError as e:
                print(f"Error parsing config file: {e}")
                print("Using default configuration")
            except Exception as e:
                print(f"Error loading config: {e}")
                print("Using default configuration")
        else:
            print(f"Config file not found at {self.config_path}")
            print("Using default configuration")

        # Validate configuration
        config = self._validate_config(config)

        return config

    def _validate_config(self, config: Dict) -> Dict:
        """
        Validate and sanitize configuration values.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Validated configuration dictionary
        """
        # Validate monitoring interval
        if not isinstance(config.get("monitoring_interval_seconds"), (int, float)):
            config["monitoring_interval_seconds"] = 30
        else:
            config["monitoring_interval_seconds"] = max(5, min(300, config["monitoring_interval_seconds"]))

        # Validate high power threshold
        if not isinstance(config.get("high_power_threshold_percent_per_10min"), (int, float)):
            config["high_power_threshold_percent_per_10min"] = 2.0
        else:
            config["high_power_threshold_percent_per_10min"] = max(0.1, min(50.0, config["high_power_threshold_percent_per_10min"]))

        # Validate battery percentages
        if not isinstance(config.get("low_battery_warning_percent"), (int, float)):
            config["low_battery_warning_percent"] = 20
        else:
            config["low_battery_warning_percent"] = max(5, min(50, config["low_battery_warning_percent"]))

        if not isinstance(config.get("critical_battery_percent"), (int, float)):
            config["critical_battery_percent"] = 10
        else:
            config["critical_battery_percent"] = max(1, min(20, config["critical_battery_percent"]))

        # Ensure critical is lower than low
        if config["critical_battery_percent"] >= config["low_battery_warning_percent"]:
            config["critical_battery_percent"] = max(1, config["low_battery_warning_percent"] - 5)

        # Validate notification cooldown
        if not isinstance(config.get("notification_cooldown_minutes"), (int, float)):
            config["notification_cooldown_minutes"] = 15
        else:
            config["notification_cooldown_minutes"] = max(1, min(120, config["notification_cooldown_minutes"]))

        # Validate data retention
        if not isinstance(config.get("data_retention_days"), (int, float)):
            config["data_retention_days"] = 30
        else:
            config["data_retention_days"] = max(1, min(365, config["data_retention_days"]))

        # Validate log level
        if config.get("log_level") not in self.VALID_LOG_LEVELS:
            config["log_level"] = "INFO"

        # Validate boolean settings
        if not isinstance(config.get("enable_notifications"), bool):
            config["enable_notifications"] = True

        if not isinstance(config.get("auto_start_monitoring"), bool):
            config["auto_start_monitoring"] = True

        return config

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value
        """
        with self.lock:
            return self.config.get(key, default)

    def get_all(self) -> Dict:
        """
        Get all configuration values.

        Returns:
            Copy of configuration dictionary
        """
        with self.lock:
            return self.config.copy()

    def update(self, updates: Dict) -> bool:
        """
        Update multiple configuration values.

        Args:
            updates: Dictionary of key-value pairs to update

        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                # Create updated config
                new_config = self.config.copy()
                new_config.update(updates)

                # Validate new config
                validated_config = self._validate_config(new_config)

                # Update internal config
                self.config = validated_config

                print(f"Configuration updated: {list(updates.keys())}")
                return True

            except Exception as e:
                print(f"Error updating configuration: {e}")
                return False

    def set(self, key: str, value: Any) -> bool:
        """
        Set a single configuration value.

        Args:
            key: Configuration key
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        return self.update({key: value})

    def save(self) -> bool:
        """
        Save configuration to file.

        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                # Ensure parent directory exists
                self.config_path.parent.mkdir(parents=True, exist_ok=True)

                # Write config to file with nice formatting
                with open(self.config_path, 'w') as f:
                    json.dump(self.config, f, indent=2)

                print(f"Configuration saved to {self.config_path}")
                return True

            except Exception as e:
                print(f"Error saving configuration: {e}")
                return False

    def reset_to_defaults(self) -> bool:
        """
        Reset configuration to default values.

        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                self.config = self.DEFAULT_CONFIG.copy()
                print("Configuration reset to defaults")
                return True

            except Exception as e:
                print(f"Error resetting configuration: {e}")
                return False

    def reload(self) -> bool:
        """
        Reload configuration from file.

        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                self.config = self._load_config()
                print("Configuration reloaded")
                return True

            except Exception as e:
                print(f"Error reloading configuration: {e}")
                return False

    def export_to_dict(self) -> Dict:
        """
        Export configuration as dictionary.

        Returns:
            Configuration dictionary
        """
        with self.lock:
            return self.config.copy()

    def import_from_dict(self, config_dict: Dict) -> bool:
        """
        Import configuration from dictionary.

        Args:
            config_dict: Configuration dictionary to import

        Returns:
            True if successful, False otherwise
        """
        with self.lock:
            try:
                # Validate imported config
                validated_config = self._validate_config(config_dict)
                self.config = validated_config
                print("Configuration imported")
                return True

            except Exception as e:
                print(f"Error importing configuration: {e}")
                return False
