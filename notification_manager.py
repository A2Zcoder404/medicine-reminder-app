"""
Notification Manager for Medicine Reminder App
Handles cross-platform notifications using Plyer
"""

import threading
import time
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from plyer import notification
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.running = False
        self.notification_thread = None
        self.check_interval = 60  # Check every minute
        self.on_reminder_due = None
        self._last_reset_date_ist = None
    
    def start_notification_service(self):
        """Start the background notification service"""
        if not self.running:
            self.running = True
            self.notification_thread = threading.Thread(target=self._notification_loop, daemon=True)
            self.notification_thread.start()
            logger.info("Notification service started")
    
    def stop_notification_service(self):
        """Stop the background notification service"""
        self.running = False
        if self.notification_thread:
            self.notification_thread.join()
        logger.info("Notification service stopped")

    def set_on_reminder_due(self, callback):
        """Set a callback to be invoked when a reminder is due. Callback(reminder_dict)."""
        self.on_reminder_due = callback
    
    def _notification_loop(self):
        """Main notification loop that runs in background"""
        while self.running:
            try:
                self._check_and_send_notifications()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in notification loop: {e}")
                time.sleep(self.check_interval)
    
    def _check_and_send_notifications(self):
        """Check for due reminders and send notifications"""
        ist = timezone(timedelta(hours=5, minutes=30))
        now_ist_dt = datetime.now(ist)
        today = now_ist_dt.date()
        current_time = now_ist_dt.time()
        
        # Reset daily taken flags once per IST day change
        if self._last_reset_date_ist != today:
            try:
                self.db_manager.reset_daily_taken_flags(today)
                self._last_reset_date_ist = today
                logger.info("Daily taken flags reset for %s (IST)", today)
            except Exception as e:
                logger.error("Failed to reset daily taken flags: %s", e)
        
        # Get all reminders for today (filtered by weekday rules)
        reminders = self.db_manager.get_reminders_for_date_filtered_by_weekday(today)

        for reminder in reminders:
            try:
                # Check intake_logs for today
                # Use context manager for database connection
                with sqlite3.connect(self.db_manager.db_path) as db:
                    cur = db.cursor()
                    cur.execute('SELECT status FROM intake_logs WHERE reminder_id = ? AND intake_date = ?', 
                              (reminder['id'], today))
                    log_row = cur.fetchone()
                is_taken_today = log_row and log_row[0] == 'taken'
                
                if is_taken_today:
                    continue

                # Parse the scheduled time
                reminder_time = datetime.strptime(reminder['specific_time'], '%H:%M').time()
                reminder_dt = datetime.combine(today, reminder_time).replace(tzinfo=ist)
                delta = (reminder_dt - now_ist_dt).total_seconds()

                # Send notifications in these cases:
                # 1. 10 minutes before the scheduled time
                # 2. Every minute after the scheduled time until marked as taken
                should_notify = False
                
                if 540 <= delta <= 660:  # 9-11 minutes before scheduled time
                    should_notify = True
                    logger.info(f"Pre-reminder notification for {reminder['medicine_name']}")
                elif delta <= 0:  # Past scheduled time
                    # If it's within the same minute as last check or over 12 hours late, skip
                    minutes_late = abs(int(delta / 60))
                    if minutes_late <= 720:  # Within 12 hours
                        should_notify = True
                        logger.info(f"Overdue reminder notification for {reminder['medicine_name']} ({minutes_late} minutes late)")

                if should_notify:
                    self._send_notification(reminder)
                    if self.on_reminder_due:
                        try:
                            self.on_reminder_due(reminder)
                        except Exception as cb_err:
                            logger.error("on_reminder_due callback failed: %s", cb_err)
                            
            except ValueError as e:
                logger.error(f"Error processing reminder {reminder['id']}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error processing reminder {reminder['id']}: {e}")
    
    def _send_notification(self, reminder: Dict):
        """Send a notification for a specific reminder"""
        try:
            title = f"💊 Medicine Reminder - {reminder['medicine_name']}"
            message = f"Time to take {reminder['dose']} of {reminder['medicine_name']}"
            
            if reminder['take_with_food']:
                message += " (Take with food)"
            
            # Send notification
            notification.notify(
                title=title,
                message=message,
                app_name="Medicine Reminder",
                timeout=10
            )
            
            logger.info(f"Notification sent for reminder {reminder['id']}: {reminder['medicine_name']}")
            
        except Exception as e:
            logger.error(f"Failed to send notification for reminder {reminder['id']}: {e}")
    
    def send_test_notification(self):
        """Send a test notification"""
        try:
            notification.notify(
                title="💊 Medicine Reminder - Test",
                message="This is a test notification from Medicine Reminder App",
                app_name="Medicine Reminder",
                timeout=5
            )
            logger.info("Test notification sent")
        except Exception as e:
            logger.error(f"Failed to send test notification: {e}")
    
    def send_immediate_notification(self, medicine_name: str, dose: str, take_with_food: bool = True):
        """Send an immediate notification (for testing or manual triggers)"""
        try:
            title = f"💊 Medicine Reminder - {medicine_name}"
            message = f"Time to take {dose} of {medicine_name}"
            
            if take_with_food:
                message += " (Take with food)"
            
            notification.notify(
                title=title,
                message=message,
                app_name="Medicine Reminder",
                timeout=10
            )
            
            logger.info(f"Immediate notification sent for {medicine_name}")
            
        except Exception as e:
            logger.error(f"Failed to send immediate notification: {e}")
