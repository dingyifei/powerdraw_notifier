"""
Cross-platform notification system for power monitoring alerts.
"""

import logging
import platform
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger("PowerMonitor.Notifier")


class NotificationType(Enum):
    """Types of notifications that can be sent."""
    LOW_BATTERY = "low_battery"
    CRITICAL_BATTERY = "critical_battery"
    HIGH_POWER_DRAW = "high_power_draw"
    UNUSUAL_DRAIN = "unusual_drain"


class PowerNotifier:
    """Handles cross-platform notifications for power monitoring events."""

    def __init__(self, config):
        """
        Initialize the power notifier.

        Args:
            config: Configuration object containing notification settings
        """
        self.config = config
        self.last_notifications: Dict[NotificationType, datetime] = {}
        self._notification_module = None
        self._initialize_notification_system()

        logger.info("PowerNotifier initialized")

    def _initialize_notification_system(self):
        """Initialize the notification system with fallback for PyInstaller builds."""
        try:
            # Try standard plyer import
            from plyer import notification
            self._notification_module = notification
            logger.debug("Initialized notification system using plyer")
        except (ImportError, NotImplementedError) as e:
            logger.warning(f"Failed to import plyer normally: {e}")

            # Fallback for PyInstaller builds - direct platform import
            try:
                system = platform.system().lower()
                if system == 'windows':
                    from plyer.platforms.win import notification
                elif system == 'darwin':
                    from plyer.platforms.macosx import notification
                elif system == 'linux':
                    from plyer.platforms.linux import notification
                else:
                    logger.error(f"Unsupported platform: {system}")
                    return

                self._notification_module = notification
                logger.debug(f"Initialized notification system using direct platform import for {system}")
            except (ImportError, NotImplementedError) as e:
                logger.error(f"Failed to initialize notification system: {e}")

    def should_notify(self, notification_type: NotificationType) -> bool:
        """
        Check if enough time has passed since the last notification of this type.

        Args:
            notification_type: The type of notification to check

        Returns:
            True if notification should be sent, False otherwise
        """
        cooldown_minutes = self.config.get('notification_cooldown_minutes', 15)

        if notification_type not in self.last_notifications:
            return True

        last_notification_time = self.last_notifications[notification_type]
        time_elapsed = datetime.now() - last_notification_time
        cooldown_period = timedelta(minutes=cooldown_minutes)

        should_send = time_elapsed >= cooldown_period

        if not should_send:
            remaining = cooldown_period - time_elapsed
            logger.debug(
                f"Notification cooldown active for {notification_type.value}. "
                f"Time remaining: {remaining.total_seconds():.0f}s"
            )

        return should_send

    def _send_notification(
        self,
        title: str,
        message: str,
        notification_type: NotificationType
    ) -> bool:
        """
        Send a notification and update the last notification time.

        Args:
            title: Notification title (max 50 characters)
            message: Notification message (max 200 characters)
            notification_type: Type of notification being sent

        Returns:
            True if notification was sent successfully, False otherwise
        """
        if not self._notification_module:
            logger.warning("Notification system not initialized, cannot send notification")
            return False

        if not self.should_notify(notification_type):
            return False

        # Truncate title and message to specified limits
        title = title[:50]
        message = message[:200]

        try:
            # Determine icon format based on platform
            system = platform.system().lower()
            icon_extension = '.ico' if system == 'windows' else '.png'
            app_icon = f'resources/icon{icon_extension}'

            self._notification_module.notify(
                title=title,
                message=message,
                app_name='Power Monitor',
                app_icon=app_icon,
                timeout=10
            )

            # Update last notification time
            self.last_notifications[notification_type] = datetime.now()

            logger.info(f"Sent {notification_type.value} notification: {title}")
            return True

        except NotImplementedError:
            logger.error(
                "Notifications not implemented for this platform. "
                "Please install required system dependencies."
            )
            return False
        except Exception as e:
            logger.error(f"Failed to send notification: {e}", exc_info=True)
            return False

    def notify_low_battery(self, percent: float) -> bool:
        """
        Send a low battery notification.

        Args:
            percent: Current battery percentage

        Returns:
            True if notification was sent successfully, False otherwise
        """
        title = "Low Battery Warning"
        message = f"Battery level at {percent:.0f}%. Consider charging soon."

        return self._send_notification(
            title=title,
            message=message,
            notification_type=NotificationType.LOW_BATTERY
        )

    def notify_critical_battery(self, percent: float) -> bool:
        """
        Send a critical battery notification.

        Args:
            percent: Current battery percentage

        Returns:
            True if notification was sent successfully, False otherwise
        """
        title = "Critical Battery Level"
        message = f"Battery critically low at {percent:.0f}%! Charge immediately."

        return self._send_notification(
            title=title,
            message=message,
            notification_type=NotificationType.CRITICAL_BATTERY
        )

    def notify_high_power_draw(
        self,
        analysis: Dict,
        battery_percent: float
    ) -> bool:
        """
        Send a high power draw notification with primary cause.

        Args:
            analysis: Power analysis dict containing 'primary_cause' and other data
            battery_percent: Current battery percentage

        Returns:
            True if notification was sent successfully, False otherwise
        """
        title = "High Power Draw Detected"

        # Extract primary cause from analysis
        primary_cause = "Unknown"
        if analysis and 'primary_cause' in analysis:
            cause_data = analysis['primary_cause']
            if isinstance(cause_data, dict):
                process_name = cause_data.get('process', 'Unknown')
                cpu_usage = cause_data.get('cpu_percent', 0)
                primary_cause = f"{process_name} ({cpu_usage:.0f}% CPU)"
            else:
                primary_cause = str(cause_data)

        message = f"Primary cause: {primary_cause}. Battery at {battery_percent:.0f}%."

        return self._send_notification(
            title=title,
            message=message,
            notification_type=NotificationType.HIGH_POWER_DRAW
        )

    def notify_unusual_drain(
        self,
        power_draw: float,
        battery_percent: float
    ) -> bool:
        """
        Send an unusual battery drain notification.

        Args:
            power_draw: Current power draw in watts
            battery_percent: Current battery percentage

        Returns:
            True if notification was sent successfully, False otherwise
        """
        title = "Unusual Battery Drain"
        message = (
            f"Abnormal power consumption detected: {power_draw:.1f}W. "
            f"Battery at {battery_percent:.0f}%."
        )

        return self._send_notification(
            title=title,
            message=message,
            notification_type=NotificationType.UNUSUAL_DRAIN
        )
