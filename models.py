"""
Data models for Medicine Reminder App
"""

from dataclasses import dataclass
from datetime import datetime, date, time
from typing import Optional, List
from enum import Enum

class TimeSlot(Enum):
    MORNING = "Morning"
    AFTERNOON = "Afternoon"
    EVENING = "Evening"
    NIGHT = "Night"

@dataclass
class User:
    id: int
    name: str
    is_self: bool = False
    created_at: Optional[datetime] = None
    
    def __str__(self):
        return self.name

@dataclass
class Reminder:
    id: int
    user_id: int
    medicine_name: str
    dose: str
    time_slot: str
    specific_time: str
    start_date: date
    end_date: date
    take_with_food: bool = True
    medicine_image_path: Optional[str] = None
    is_taken: bool = False
    taken_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    user_name: Optional[str] = None
    
    def __str__(self):
        return f"{self.medicine_name} - {self.specific_time}"
    
    @property
    def status_color(self) -> str:
        """Return color code for reminder status"""
        if self.is_taken:
            return "green"
        else:
            # Check if reminder is overdue
            now = datetime.now()
            reminder_datetime = datetime.combine(self.start_date, 
                                               datetime.strptime(self.specific_time, '%H:%M').time())
            if now > reminder_datetime:
                return "red"
            return "orange"
    
    @property
    def formatted_time(self) -> str:
        """Return formatted time for display"""
        try:
            time_obj = datetime.strptime(self.specific_time, '%H:%M').time()
            return time_obj.strftime('%I:%M %p').lower()
        except ValueError:
            return self.specific_time
    
    @property
    def time_slot_display(self) -> str:
        """Return formatted time slot for display"""
        return f"{self.time_slot} {self.formatted_time}"
    
    @property
    def is_overdue(self) -> bool:
        """Check if reminder is overdue"""
        if self.is_taken:
            return False
        
        now = datetime.now()
        reminder_datetime = datetime.combine(self.start_date, 
                                           datetime.strptime(self.specific_time, '%H:%M').time())
        return now > reminder_datetime
    
    @property
    def status_text(self) -> str:
        """Return status text for display"""
        if self.is_taken and self.taken_at:
            taken_time = self.taken_at.strftime('%I:%M %p').lower()
            return f"Medicine taken at: {taken_time}"
        elif self.is_overdue:
            return "Overdue"
        else:
            return "Pending"

@dataclass
class ReminderGroup:
    """Group reminders by user for display"""
    user: User
    reminders: List[Reminder]
    
    def __init__(self, user: User, reminders: List[Reminder] = None):
        self.user = user
        self.reminders = reminders or []
    
    def add_reminder(self, reminder: Reminder):
        """Add a reminder to this group"""
        self.reminders.append(reminder)
        # Sort reminders by time
        self.reminders.sort(key=lambda r: r.specific_time)
    
    def get_reminders_by_status(self, taken: bool = None) -> List[Reminder]:
        """Get reminders filtered by taken status"""
        if taken is None:
            return self.reminders
        return [r for r in self.reminders if r.is_taken == taken]
    
    def get_overdue_reminders(self) -> List[Reminder]:
        """Get overdue reminders"""
        return [r for r in self.reminders if r.is_overdue and not r.is_taken]
    
    def get_pending_reminders(self) -> List[Reminder]:
        """Get pending (not taken, not overdue) reminders"""
        return [r for r in self.reminders if not r.is_taken and not r.is_overdue]
