"""
Notification Manager for Medicine Reminder App
Handles cross-platform notifications using Plyer
"""

import threading
import time
from datetime import datetime, timedelta
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
        today = datetime.now().date()
        current_time = datetime.now().time()
        
        # Get all reminders for today
        reminders = self.db_manager.get_reminders_for_date(today)
        
        for reminder in reminders:
            # Skip if already taken
            if reminder['is_taken']:
                continue
            
            # Parse the specific time
            try:
                reminder_time = datetime.strptime(reminder['specific_time'], '%H:%M').time()
                
                # Check if it's time for this reminder (within 5 minutes)
                time_diff = abs((datetime.combine(today, current_time) - 
                               datetime.combine(today, reminder_time)).total_seconds())
                
                if time_diff <= 300:  # 5 minutes tolerance
                    self._send_notification(reminder)
                    
            except ValueError as e:
                logger.error(f"Error parsing time for reminder {reminder['id']}: {e}")
    
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
