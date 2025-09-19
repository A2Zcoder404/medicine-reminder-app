"""
Main Medicine Reminder Application
Desktop version using Tkinter
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date, timedelta
import os
from typing import List, Dict, Optional

from database import DatabaseManager
from notification_manager import NotificationManager
from models import User, Reminder, ReminderGroup, TimeSlot

class MedicineReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Medicine Reminder App")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # Initialize managers
        self.db_manager = DatabaseManager()
        self.notification_manager = NotificationManager(self.db_manager)
        
        # Current state
        self.current_date = date.today()
        self.current_user_filter = None  # None = all users, user_id = specific user
        self.is_family_view = False
        
        # Start notification service
        self.notification_manager.start_notification_service()
        
        # Create UI
        self.create_ui()
        self.refresh_reminders()
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_ui(self):
        """Create the main UI"""
        # Main container
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header section
        self.create_header(main_frame)
        
        # Reminders list
        self.create_reminders_list(main_frame)
        
        # Toggle tabs
        self.create_toggle_tabs(main_frame)
        
        # Bottom navigation
        self.create_bottom_navigation(main_frame)
    
    def create_header(self, parent):
        """Create header with date and calendar"""
        header_frame = tk.Frame(parent, bg='#4CAF50', height=80)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        header_frame.pack_propagate(False)
        
        # Date display
        date_label = tk.Label(header_frame, text=f"Today, {self.current_date.strftime('%d %b')}", 
                             font=('Arial', 16, 'bold'), fg='white', bg='#4CAF50')
        date_label.pack(pady=10)
        
        # Calendar strip
        calendar_frame = tk.Frame(header_frame, bg='#4CAF50')
        calendar_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # Generate calendar days
        start_date = self.current_date - timedelta(days=self.current_date.weekday())
        for i in range(7):
            day_date = start_date + timedelta(days=i)
            day_frame = tk.Frame(calendar_frame, bg='#4CAF50')
            day_frame.pack(side=tk.LEFT, expand=True)
            
            # Day name
            day_name = tk.Label(day_frame, text=day_date.strftime('%a'), 
                               font=('Arial', 10), fg='white', bg='#4CAF50')
            day_name.pack()
            
            # Day number
            day_num = tk.Label(day_frame, text=str(day_date.day), 
                              font=('Arial', 12, 'bold'), fg='white', bg='#4CAF50')
            day_num.pack()
            
            # Highlight current day
            if day_date == self.current_date:
                day_num.configure(bg='white', fg='#4CAF50')
    
    def create_toggle_tabs(self, parent):
        """Create toggle tabs for My Reminders / Family Reminders"""
        tabs_frame = tk.Frame(parent, bg='#f0f0f0')
        tabs_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Tab buttons
        self.my_reminders_btn = tk.Button(tabs_frame, text="My Reminders", 
                                         font=('Arial', 12, 'bold'),
                                         bg='#4CAF50', fg='white',
                                         command=self.show_my_reminders,
                                         relief=tk.FLAT, padx=20, pady=10)
        self.my_reminders_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.family_reminders_btn = tk.Button(tabs_frame, text="Family Reminders", 
                                            font=('Arial', 12, 'bold'),
                                            bg='#E0E0E0', fg='#666666',
                                            command=self.show_family_reminders,
                                            relief=tk.FLAT, padx=20, pady=10)
        self.family_reminders_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # Set initial state
        self.show_my_reminders()
    
    def create_reminders_list(self, parent):
        """Create scrollable reminders list"""
        # Create frame for list
        list_frame = tk.Frame(parent, bg='#f0f0f0')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(list_frame, bg='#f0f0f0', highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#f0f0f0')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store reference to scrollable frame
        self.reminders_frame = scrollable_frame
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def create_bottom_navigation(self, parent):
        """Create bottom navigation bar"""
        nav_frame = tk.Frame(parent, bg='white', height=60)
        nav_frame.pack(fill=tk.X, side=tk.BOTTOM)
        nav_frame.pack_propagate(False)
        
        # Navigation buttons
        nav_buttons = [
            ("⏰", "Reminders", self.show_reminders),
            ("👥", "Family", self.show_family),
            ("", "", None),  # Space for FAB
            ("💊", "Medicines", self.show_medicines),
            ("⚙", "Settings", self.show_settings)
        ]
        
        for i, (icon, text, command) in enumerate(nav_buttons):
            if icon == "":  # FAB position
                fab_frame = tk.Frame(nav_frame, bg='white')
                fab_frame.pack(side=tk.LEFT, expand=True)
                
                fab_btn = tk.Button(fab_frame, text="+", font=('Arial', 20, 'bold'),
                                   bg='#4CAF50', fg='white', width=3, height=1,
                                   command=self.add_reminder, relief=tk.FLAT)
                fab_btn.pack(pady=10)
            else:
                btn_frame = tk.Frame(nav_frame, bg='white')
                btn_frame.pack(side=tk.LEFT, expand=True)
                
                btn = tk.Button(btn_frame, text=f"{icon}\n{text}", 
                               font=('Arial', 10), bg='white', fg='#666666',
                               command=command, relief=tk.FLAT, padx=10, pady=5)
                btn.pack()
    
    def show_my_reminders(self):
        """Show only my reminders"""
        self.is_family_view = False
        self.current_user_filter = None  # Will filter to self user
        
        # Update button styles
        self.my_reminders_btn.configure(bg='#4CAF50', fg='white')
        self.family_reminders_btn.configure(bg='#E0E0E0', fg='#666666')
        
        self.refresh_reminders()
    
    def show_family_reminders(self):
        """Show family reminders"""
        self.is_family_view = True
        self.current_user_filter = None  # Show all users
        
        # Update button styles
        self.my_reminders_btn.configure(bg='#E0E0E0', fg='#666666')
        self.family_reminders_btn.configure(bg='#4CAF50', fg='white')
        
        self.refresh_reminders()
    
    def refresh_reminders(self):
        """Refresh the reminders list"""
        # Clear existing reminders
        for widget in self.reminders_frame.winfo_children():
            widget.destroy()
        
        # Get reminders for current date
        if self.current_user_filter:
            reminders = self.db_manager.get_reminders_for_date(self.current_date, self.current_user_filter)
        else:
            reminders = self.db_manager.get_reminders_for_date(self.current_date)
        
        # Filter for family vs my reminders
        if not self.is_family_view:
            # Show only self reminders
            users = self.db_manager.get_users()
            self_user = next((u for u in users if u['is_self']), None)
            if self_user:
                reminders = [r for r in reminders if r['user_id'] == self_user['id']]
        
        # Group reminders by user
        user_groups = {}
        for reminder in reminders:
            user_id = reminder['user_id']
            if user_id not in user_groups:
                user_groups[user_id] = {
                    'user_name': reminder['user_name'],
                    'reminders': []
                }
            user_groups[user_id]['reminders'].append(reminder)
        
        # Create UI for each user group
        for user_id, group_data in user_groups.items():
            self.create_user_section(group_data['user_name'], group_data['reminders'])
    
    def create_user_section(self, user_name: str, reminders: List[Dict]):
        """Create a section for a user's reminders"""
        if not reminders:
            return
        
        # User section header
        header_frame = tk.Frame(self.reminders_frame, bg='#f0f0f0')
        header_frame.pack(fill=tk.X, pady=(10, 5))
        
        header_label = tk.Label(header_frame, text=f"{user_name}'s reminders", 
                               font=('Arial', 14, 'bold'), fg='#333333', bg='#f0f0f0')
        header_label.pack(anchor=tk.W)
        
        # Create reminder cards
        for reminder in reminders:
            self.create_reminder_card(reminder)
    
    def create_reminder_card(self, reminder: Dict):
        """Create a reminder card"""
        # Time slot label
        time_label = tk.Label(self.reminders_frame, 
                             text=f"{reminder['time_slot']} {reminder['specific_time']}", 
                             font=('Arial', 10, 'bold'), fg='#666666', bg='#f0f0f0')
        time_label.pack(anchor=tk.W, padx=(20, 0), pady=(5, 0))
        
        # Card frame
        card_frame = tk.Frame(self.reminders_frame, bg='white', relief=tk.RAISED, bd=1)
        card_frame.pack(fill=tk.X, padx=20, pady=2)
        
        # Left side - status strip and pill icon
        left_frame = tk.Frame(card_frame, bg='white', width=60)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)
        left_frame.pack_propagate(False)
        
        # Status strip
        status_color = '#4CAF50' if reminder['is_taken'] else ('#FF5722' if self.is_overdue(reminder) else '#FF9800')
        status_strip = tk.Frame(left_frame, bg=status_color, width=4)
        status_strip.pack(side=tk.LEFT, fill=tk.Y)
        
        # Pill icon
        pill_label = tk.Label(left_frame, text="💊", font=('Arial', 20), 
                             bg='white', fg='#666666')
        pill_label.pack(expand=True)
        
        # Right side - medicine details
        right_frame = tk.Frame(card_frame, bg='white')
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Medicine name
        medicine_label = tk.Label(right_frame, text=reminder['medicine_name'], 
                                 font=('Arial', 12, 'bold'), fg='#333333', bg='white')
        medicine_label.pack(anchor=tk.W)
        
        # Take with food
        if reminder['take_with_food']:
            food_label = tk.Label(right_frame, text="Take with food", 
                                 font=('Arial', 10), fg='#666666', bg='white')
            food_label.pack(anchor=tk.W)
        
        # Dose info
        dose_label = tk.Label(right_frame, text=f"Dose: {reminder['dose']}", 
                             font=('Arial', 10), fg='#FF5722', bg='white')
        dose_label.pack(anchor=tk.W)
        
        # Status
        if reminder['is_taken'] and reminder['taken_at']:
            taken_time = datetime.strptime(reminder['taken_at'], '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p').lower()
            status_label = tk.Label(right_frame, text=f"Medicine taken at: {taken_time}", 
                                   font=('Arial', 10), fg='#4CAF50', bg='white')
            status_label.pack(anchor=tk.W)
        elif self.is_overdue(reminder):
            status_label = tk.Label(right_frame, text="Overdue", 
                                   font=('Arial', 10), fg='#FF5722', bg='white')
            status_label.pack(anchor=tk.W)
        
        # Action buttons
        action_frame = tk.Frame(right_frame, bg='white')
        action_frame.pack(anchor=tk.W, pady=(5, 0))
        
        if not reminder['is_taken']:
            taken_btn = tk.Button(action_frame, text="Mark as Taken", 
                                 font=('Arial', 9), bg='#4CAF50', fg='white',
                                 command=lambda: self.mark_reminder_taken(reminder['id']),
                                 relief=tk.FLAT, padx=10, pady=2)
            taken_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        edit_btn = tk.Button(action_frame, text="Edit", 
                            font=('Arial', 9), bg='#2196F3', fg='white',
                            command=lambda: self.edit_reminder(reminder['id']),
                            relief=tk.FLAT, padx=10, pady=2)
        edit_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        delete_btn = tk.Button(action_frame, text="Delete", 
                              font=('Arial', 9), bg='#F44336', fg='white',
                              command=lambda: self.delete_reminder(reminder['id']),
                              relief=tk.FLAT, padx=10, pady=2)
        delete_btn.pack(side=tk.LEFT)
    
    def is_overdue(self, reminder: Dict) -> bool:
        """Check if reminder is overdue"""
        if reminder['is_taken']:
            return False
        
        now = datetime.now()
        reminder_time = datetime.strptime(reminder['specific_time'], '%H:%M').time()
        reminder_datetime = datetime.combine(self.current_date, reminder_time)
        
        return now > reminder_datetime
    
    def mark_reminder_taken(self, reminder_id: int):
        """Mark a reminder as taken"""
        if self.db_manager.mark_reminder_taken(reminder_id):
            messagebox.showinfo("Success", "Reminder marked as taken!")
            self.refresh_reminders()
        else:
            messagebox.showerror("Error", "Failed to mark reminder as taken")
    
    def add_reminder(self):
        """Open add reminder dialog"""
        AddReminderDialog(self.root, self.db_manager, self.refresh_reminders)
    
    def edit_reminder(self, reminder_id: int):
        """Open edit reminder dialog"""
        reminder = self.db_manager.get_reminder_by_id(reminder_id)
        if reminder:
            AddReminderDialog(self.root, self.db_manager, self.refresh_reminders, reminder)
    
    def delete_reminder(self, reminder_id: int):
        """Delete a reminder"""
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this reminder?"):
            if self.db_manager.delete_reminder(reminder_id):
                messagebox.showinfo("Success", "Reminder deleted!")
                self.refresh_reminders()
            else:
                messagebox.showerror("Error", "Failed to delete reminder")
    
    def show_reminders(self):
        """Show reminders page"""
        pass  # Already on reminders page
    
    def show_family(self):
        """Show family page"""
        self.show_family_reminders()
    
    def show_medicines(self):
        """Show medicines page"""
        messagebox.showinfo("Info", "Medicines page - Coming soon!")
    
    def show_settings(self):
        """Show settings page"""
        SettingsDialog(self.root, self.notification_manager)
    
    def on_closing(self):
        """Handle application closing"""
        self.notification_manager.stop_notification_service()
        self.root.destroy()


class AddReminderDialog:
    """Dialog for adding/editing reminders"""
    
    def __init__(self, parent, db_manager, callback, reminder=None):
        self.db_manager = db_manager
        self.callback = callback
        self.reminder = reminder
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Reminder" if not reminder else "Edit Reminder")
        self.dialog.geometry("500x600")
        self.dialog.configure(bg='#f0f0f0')
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.create_form()
    
    def create_form(self):
        """Create the reminder form"""
        main_frame = tk.Frame(self.dialog, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text="Create new reminder", 
                              font=('Arial', 16, 'bold'), fg='#333333', bg='#f0f0f0')
        title_label.pack(pady=(0, 20))
        
        # Time of day selection
        time_frame = tk.Frame(main_frame, bg='#f0f0f0')
        time_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(time_frame, text="Time of Day:", font=('Arial', 12, 'bold'), 
                fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        
        time_buttons_frame = tk.Frame(time_frame, bg='#f0f0f0')
        time_buttons_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.time_slot_var = tk.StringVar(value="Morning")
        time_slots = ["Morning", "Afternoon", "Evening", "Night"]
        
        for i, slot in enumerate(time_slots):
            btn = tk.Radiobutton(time_buttons_frame, text=slot, variable=self.time_slot_var, 
                               value=slot, font=('Arial', 10), bg='#f0f0f0')
            btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Form fields
        fields_frame = tk.Frame(main_frame, bg='#f0f0f0')
        fields_frame.pack(fill=tk.BOTH, expand=True)
        
        # Patient selection
        self.create_field(fields_frame, "Patient:", "patient", "Myself")
        
        # Number of days
        self.create_field(fields_frame, "Number of Days:", "days", "7")
        
        # Select time
        self.create_field(fields_frame, "Select Time:", "time", "08:00")
        
        # Medicine name
        self.create_field(fields_frame, "For which medicine?:", "medicine", "Enter Medicine name")
        
        # Select dose
        self.create_field(fields_frame, "Select Dose:", "dose", "1x")
        
        # Upload image section
        image_frame = tk.Frame(fields_frame, bg='#E8F5E8', relief=tk.RAISED, bd=1)
        image_frame.pack(fill=tk.X, pady=10)
        
        image_label = tk.Label(image_frame, text="📷 Upload Medicine Image", 
                              font=('Arial', 12), fg='#4CAF50', bg='#E8F5E8')
        image_label.pack(pady=20)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        save_btn = tk.Button(button_frame, text="Save Reminder", 
                            font=('Arial', 12, 'bold'), bg='#4CAF50', fg='white',
                            command=self.save_reminder, relief=tk.FLAT, padx=20, pady=10)
        save_btn.pack(side=tk.RIGHT)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", 
                              font=('Arial', 12), bg='#E0E0E0', fg='#666666',
                              command=self.dialog.destroy, relief=tk.FLAT, padx=20, pady=10)
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Load existing data if editing
        if self.reminder:
            self.load_reminder_data()
    
    def create_field(self, parent, label_text, field_name, placeholder):
        """Create a form field"""
        field_frame = tk.Frame(parent, bg='#f0f0f0')
        field_frame.pack(fill=tk.X, pady=5)
        
        label = tk.Label(field_frame, text=label_text, font=('Arial', 10, 'bold'), 
                        fg='#333333', bg='#f0f0f0')
        label.pack(anchor=tk.W)
        
        if field_name == "patient":
            # Patient dropdown
            users = self.db_manager.get_users()
            user_names = [u['name'] for u in users]
            
            var = tk.StringVar(value=user_names[0] if user_names else "Myself")
            dropdown = ttk.Combobox(field_frame, textvariable=var, values=user_names, 
                                   state="readonly", font=('Arial', 10))
            dropdown.pack(fill=tk.X, pady=(2, 0))
            setattr(self, f"{field_name}_var", var)
            
        elif field_name == "time":
            # Time dropdown
            times = [f"{h:02d}:{m:02d}" for h in range(24) for m in range(0, 60, 30)]
            var = tk.StringVar(value="08:00")
            dropdown = ttk.Combobox(field_frame, textvariable=var, values=times, 
                                   state="readonly", font=('Arial', 10))
            dropdown.pack(fill=tk.X, pady=(2, 0))
            setattr(self, f"{field_name}_var", var)
            
        elif field_name == "dose":
            # Dose dropdown
            doses = ["1x", "2x", "3x", "4x", "5x", "6x"]
            var = tk.StringVar(value="1x")
            dropdown = ttk.Combobox(field_frame, textvariable=var, values=doses, 
                                   state="readonly", font=('Arial', 10))
            dropdown.pack(fill=tk.X, pady=(2, 0))
            setattr(self, f"{field_name}_var", var)
            
        else:
            # Text entry
            var = tk.StringVar()
            entry = tk.Entry(field_frame, textvariable=var, font=('Arial', 10), 
                            relief=tk.FLAT, bd=1, bg='white')
            entry.pack(fill=tk.X, pady=(2, 0))
            setattr(self, f"{field_name}_var", var)
    
    def load_reminder_data(self):
        """Load existing reminder data for editing"""
        if not self.reminder:
            return
        
        self.time_slot_var.set(self.reminder['time_slot'])
        self.patient_var.set(self.reminder['user_name'])
        self.days_var.set(str((datetime.strptime(self.reminder['end_date'], '%Y-%m-%d') - 
                              datetime.strptime(self.reminder['start_date'], '%Y-%m-%d')).days + 1))
        self.time_var.set(self.reminder['specific_time'])
        self.medicine_var.set(self.reminder['medicine_name'])
        self.dose_var.set(self.reminder['dose'])
    
    def save_reminder(self):
        """Save the reminder"""
        try:
            # Get form data
            time_slot = self.time_slot_var.get()
            patient_name = self.patient_var.get()
            days = int(self.days_var.get())
            specific_time = self.time_var.get()
            medicine_name = self.medicine_var.get()
            dose = self.dose_var.get()
            
            # Validate
            if not medicine_name.strip():
                messagebox.showerror("Error", "Please enter medicine name")
                return
            
            # Get user ID
            users = self.db_manager.get_users()
            user = next((u for u in users if u['name'] == patient_name), None)
            if not user:
                messagebox.showerror("Error", "Invalid patient selected")
                return
            
            # Calculate dates
            start_date = date.today()
            end_date = start_date + timedelta(days=days-1)
            
            if self.reminder:
                # Update existing reminder
                success = self.db_manager.update_reminder(
                    self.reminder['id'],
                    user_id=user['id'],
                    medicine_name=medicine_name,
                    dose=dose,
                    time_slot=time_slot,
                    specific_time=specific_time,
                    start_date=start_date,
                    end_date=end_date,
                    take_with_food=True
                )
                if success:
                    messagebox.showinfo("Success", "Reminder updated!")
                    self.dialog.destroy()
                    self.callback()
                else:
                    messagebox.showerror("Error", "Failed to update reminder")
            else:
                # Add new reminder
                reminder_id = self.db_manager.add_reminder(
                    user['id'], medicine_name, dose, time_slot, 
                    specific_time, start_date, end_date, True
                )
                if reminder_id:
                    messagebox.showinfo("Success", "Reminder added!")
                    self.dialog.destroy()
                    self.callback()
                else:
                    messagebox.showerror("Error", "Failed to add reminder")
                    
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid input: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")


class SettingsDialog:
    """Settings dialog"""
    
    def __init__(self, parent, notification_manager):
        self.notification_manager = notification_manager
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("400x300")
        self.dialog.configure(bg='#f0f0f0')
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
        
        self.create_settings()
    
    def create_settings(self):
        """Create settings interface"""
        main_frame = tk.Frame(self.dialog, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Title
        title_label = tk.Label(main_frame, text="Settings", 
                              font=('Arial', 16, 'bold'), fg='#333333', bg='#f0f0f0')
        title_label.pack(pady=(0, 20))
        
        # Notification settings
        notif_frame = tk.Frame(main_frame, bg='#f0f0f0')
        notif_frame.pack(fill=tk.X, pady=10)
        
        tk.Label(notif_frame, text="Notifications", font=('Arial', 12, 'bold'), 
                fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        
        test_btn = tk.Button(notif_frame, text="Test Notification", 
                            font=('Arial', 10), bg='#4CAF50', fg='white',
                            command=self.test_notification, relief=tk.FLAT, padx=15, pady=5)
        test_btn.pack(anchor=tk.W, pady=(5, 0))
        
        # Close button
        close_btn = tk.Button(main_frame, text="Close", 
                             font=('Arial', 12), bg='#E0E0E0', fg='#666666',
                             command=self.dialog.destroy, relief=tk.FLAT, padx=20, pady=10)
        close_btn.pack(side=tk.BOTTOM, pady=(20, 0))
    
    def test_notification(self):
        """Test notification"""
        self.notification_manager.send_test_notification()


def main():
    """Main function"""
    root = tk.Tk()
    app = MedicineReminderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
