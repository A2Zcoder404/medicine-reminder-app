"""
Main Medicine Reminder Application
Desktop version using Tkinter
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date, timedelta, timezone
import os
from typing import List, Dict, Optional

from database import DatabaseManager
from notification_manager import NotificationManager
from models import User, Reminder, ReminderGroup, TimeSlot
from auth_manager import AuthManager, LoginDialog, ChangePasswordDialog
import sqlite3

class MedicineReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Medicine Reminder App")
        self.root.geometry("800x600")
        self.root.configure(bg='#f0f0f0')
        
        # Initialize managers
        self.db_manager = DatabaseManager()
        self.auth_manager = AuthManager(self.db_manager)
        self.notification_manager = NotificationManager(self.db_manager)
        
        # Set up authentication callbacks
        self.auth_manager.set_login_callback(self.on_user_login)
        self.auth_manager.set_logout_callback(self.on_user_logout)
        
        # Current state
        self.current_date = date.today()
        self.current_user_filter = None  # None = all users, user_id = specific user
        self.is_family_view = False
        
        # Check if user is logged in, if not show login dialog
        if not self.auth_manager.is_logged_in():
            self.show_login_dialog()
        else:
            self.initialize_app()
    
    def show_login_dialog(self):
        """Show login dialog"""
        LoginDialog(self.root, self.auth_manager, self.initialize_app)
    
    def initialize_app(self):
        """Initialize the application after successful login"""
        # Start notification service with UI callback for due reminders
        self.notification_manager.set_on_reminder_due(lambda r: self.root.after(0, lambda: self._on_reminder_due_from_service(r)))
        self.notification_manager.start_notification_service()
        
        # Create UI
        self.create_ui()
        self.refresh_reminders()
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_user_login(self, user: Dict):
        """Called when user logs in"""
        self.root.title(f"Medicine Reminder App - {user['name']}")
    
    def on_user_logout(self, user: Dict):
        """Called when user logs out"""
        # Clear all data and reset UI
        self.clear_user_data()
        self.root.title("Medicine Reminder App")
        # Show login dialog again
        self.show_login_dialog()
    
    def clear_user_data(self):
        """Clear all user-specific data from the UI"""
        # Stop notification service
        self.notification_manager.stop_notification_service()
        
        # Clear reminders display
        if hasattr(self, 'reminders_frame'):
            for widget in self.reminders_frame.winfo_children():
                widget.destroy()
        
        # Reset state
        self.current_date = date.today()
        self.current_user_filter = None
        self.is_family_view = False
    
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
        self.date_label = tk.Label(header_frame, text=f"Today, {self.current_date.strftime('%d %b')}", 
                             font=('Arial', 16, 'bold'), fg='white', bg='#4CAF50')
        self.date_label.pack(pady=10)
        
        # Calendar strip
        calendar_frame = tk.Frame(header_frame, bg='#4CAF50')
        calendar_frame.pack(fill=tk.X, padx=20, pady=(0, 10))
        
        # Generate calendar buttons for days
        self.calendar_buttons = []
        start_date = self.current_date - timedelta(days=self.current_date.weekday())
        for i in range(7):
            day_date = start_date + timedelta(days=i)
            btn = tk.Button(calendar_frame, text=f"{day_date.strftime('%a')}",
                            font=('Arial', 10), fg='white', bg='#4CAF50',
                            relief=tk.RAISED, bd=0,
                            activebackground='#3e8e41', activeforeground='white',
                            command=lambda d=day_date: self.set_current_date(d))
            btn.pack(side=tk.LEFT, expand=True, padx=4)
            self.calendar_buttons.append((btn, day_date))
        self._highlight_selected_calendar_day()
        
        # Date jump controls (Go to specific date)
        jump_frame = tk.Frame(header_frame, bg='#4CAF50')
        jump_frame.place(relx=0.95, rely=0.15, anchor='ne')

        tk.Label(jump_frame, text="Go to:", font=('Arial', 10, 'bold'), fg='white', bg='#4CAF50').pack(side=tk.LEFT, padx=(0,6))
        self.goto_var = tk.StringVar(value=self.current_date.strftime('%Y-%m-%d'))
        goto_entry = tk.Entry(jump_frame, textvariable=self.goto_var, width=10, font=('Arial', 10))
        goto_entry.pack(side=tk.LEFT)
        goto_btn = tk.Button(jump_frame, text="Go", font=('Arial', 9), bg='white', fg='#4CAF50', command=self._goto_date, relief=tk.FLAT)
        goto_btn.pack(side=tk.LEFT, padx=(6,0))

    def _highlight_selected_calendar_day(self):
        """Highlight the selected day button in the header strip."""
        if not hasattr(self, 'calendar_buttons'):
            return
        for btn, d in self.calendar_buttons:
            if d == self.current_date:
                btn.configure(bg='white', fg='#4CAF50', relief=tk.SUNKEN)
            else:
                btn.configure(bg='#4CAF50', fg='white', relief=tk.RAISED)

    def set_current_date(self, new_date: date):
        """Set the current date and refresh UI and highlight."""
        self.current_date = new_date
        if hasattr(self, 'date_label'):
            self.date_label.configure(text=f"Today, {self.current_date.strftime('%d %b')}")
        self._highlight_selected_calendar_day()
        self.refresh_reminders()

    def _goto_date(self):
        """Handler for the Go button in header - parses YYYY-MM-DD and jumps to that date."""
        val = (self.goto_var.get() or '').strip()
        try:
            new_d = datetime.strptime(val, '%Y-%m-%d').date()
        except Exception:
            messagebox.showerror("Error", "Please enter a valid date in YYYY-MM-DD format")
            return
        self.set_current_date(new_d)
    
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
        self.family_reminders_btn.pack(side=tk.LEFT, padx=(5, 5))

        # History button beside family
        self.history_btn = tk.Button(tabs_frame, text="History", 
                                    font=('Arial', 12, 'bold'),
                                    bg='#E0E0E0', fg='#666666',
                                    command=self.show_history,
                                    relief=tk.FLAT, padx=20, pady=10)
        self.history_btn.pack(side=tk.LEFT, padx=(5, 0))
        
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
        if hasattr(self, 'history_btn'):
            self.history_btn.configure(bg='#E0E0E0', fg='#666666')
        
        self.refresh_reminders()
    
    def show_family_reminders(self):
        """Show family reminders"""
        self.is_family_view = True
        self.current_user_filter = None  # Show all users
        
        # Update button styles
        self.my_reminders_btn.configure(bg='#E0E0E0', fg='#666666')
        self.family_reminders_btn.configure(bg='#4CAF50', fg='white')
        if hasattr(self, 'history_btn'):
            self.history_btn.configure(bg='#E0E0E0', fg='#666666')
        
        self.refresh_reminders()
    
    def refresh_reminders(self):
        """Refresh the reminders list"""
        # Clear existing reminders
        for widget in self.reminders_frame.winfo_children():
            widget.destroy()
        
        # Get reminders for current date (weekday-filtered)
        current_user = self.auth_manager.get_current_user()
        if not current_user:
            return
        
        if self.is_family_view:
            # In family view, show all reminders for this owner and their family members
            reminders = self.db_manager.get_reminders_for_date_filtered_by_weekday(
                self.current_date, 
                owner_id=current_user['id']
            )
        else:
            # In My Reminders view, show only the current user's reminders
            reminders = self.db_manager.get_reminders_for_date_filtered_by_weekday(
                self.current_date,
                user_id=current_user['id']
            )
        
        # Group reminders by user
        user_groups = {}
        for reminder in reminders:
            # Safety: ensure weekday applies (defense in depth)
            days = reminder.get('days_of_week')
            if days and days.strip() != '':
                try:
                    allowed = {int(x.strip()) for x in days.split(',') if x.strip() != ''}
                    if self.current_date.weekday() not in allowed:
                        continue
                except Exception:
                    pass
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
        """Create a reminder card, using intake_logs for today's status."""
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

        # Determine today's status from intake_logs
        today = self.current_date
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT status, taken_at FROM intake_logs WHERE reminder_id = ? AND intake_date = ?', (reminder['id'], today))
        log_row = cursor.fetchone()
        conn.close()
        is_taken_today = log_row and log_row[0] == 'taken'
        taken_at_today = log_row[1] if log_row else None

        # Status strip
        status_color = '#4CAF50' if is_taken_today else ('#FF5722' if self.is_overdue(reminder) else '#FF9800')
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
        if is_taken_today and taken_at_today:
            try:
                taken_time = datetime.strptime(taken_at_today, '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p').lower()
            except Exception:
                taken_time = taken_at_today
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

        if not is_taken_today:
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
        """Check if reminder is overdue using intake_logs for today's status."""
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        reminder_time = datetime.strptime(reminder['specific_time'], '%H:%M').time()
        reminder_datetime = datetime.combine(self.current_date, reminder_time).replace(tzinfo=ist)
        # Check intake_logs for today
        conn = sqlite3.connect(self.db_manager.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM intake_logs WHERE reminder_id = ? AND intake_date = ?', (reminder['id'], self.current_date))
        log_row = cursor.fetchone()
        conn.close()
        is_taken_today = log_row and log_row[0] == 'taken'
        # Only overdue if past scheduled time and not taken today
        return (now > reminder_datetime) and (not is_taken_today)
    
    def mark_reminder_taken(self, reminder_id: int):
        """Mark a reminder as taken and refresh history if open."""
        try:
            success = self.db_manager.mark_reminder_taken(reminder_id)
            if success:
                self.refresh_reminders()
                # Refresh history dialog if open
                for w in self.root.winfo_children():
                    if hasattr(w, 'title') and w.title() == 'Intake History':
                        # Find the HistoryDialog instance and refresh
                        for child in w.winfo_children():
                            if hasattr(child, 'refresh_table'):
                                try:
                                    child.refresh_table()
                                except Exception as e:
                                    print(f"Error refreshing history: {e}")
                messagebox.showinfo("Success", "Medicine marked as taken!")
            else:
                messagebox.showerror("Error", "Failed to mark medicine as taken. Please try again.")
        except Exception as e:
            print(f"Error marking medicine as taken: {e}")
            messagebox.showerror("Error", "Failed to mark medicine as taken. Please try again.")
    
    def add_reminder(self):
        """Open add reminder dialog (defaults to current logged-in user)"""
        AddReminderDialog(self.root, self.db_manager, self.refresh_reminders, auth_manager=self.auth_manager, selected_date=self.current_date)
    
    def edit_reminder(self, reminder_id: int):
        """Open edit reminder dialog"""
        reminder = self.db_manager.get_reminder_by_id(reminder_id)
        if reminder:
            # Only allow editing if the reminder belongs to the current user or we are in family view
            current_user = self.auth_manager.get_current_user()
            if not self.is_family_view and current_user and reminder['user_id'] != current_user['id']:
                messagebox.showerror("Permission denied", "You cannot edit another user's reminder.")
                return
            AddReminderDialog(self.root, self.db_manager, self.refresh_reminders, reminder, auth_manager=self.auth_manager)
    
    def delete_reminder(self, reminder_id: int):
        """Delete a reminder"""
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this reminder?"):
            # Check permission
            reminder = self.db_manager.get_reminder_by_id(reminder_id)
            current_user = self.auth_manager.get_current_user()
            if reminder and current_user and reminder['user_id'] != current_user['id'] and not self.is_family_view:
                messagebox.showerror("Permission denied", "You cannot delete another user's reminder.")
                return
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
        FamilyDialog(self.root, self.db_manager, self.refresh_reminders, self.auth_manager)
    
    def show_medicines(self):
        """Show medicines page"""
        messagebox.showinfo("Info", "Medicines page - Coming soon!")

    def show_history(self):
        """Open history dialog"""
        HistoryDialog(self.root, self.db_manager, auth_manager=self.auth_manager)
    
    def show_settings(self):
        """Show settings page"""
        SettingsDialog(self.root, self.notification_manager, self.auth_manager)
    
    def on_closing(self):
        """Handle application closing"""
        self.notification_manager.stop_notification_service()
        self.root.destroy()

    def _on_reminder_due_from_service(self, reminder: Dict):
        """Prompt the user to confirm medicine intake for a due reminder."""
        try:
            resp = messagebox.askyesno(
                "Medicine Confirmation",
                f"Did {reminder['user_name']} take {reminder['medicine_name']} ({reminder['dose']})?"
            )
            if resp:
                self.db_manager.mark_reminder_taken(reminder['id'])
            else:
                self.db_manager.mark_reminder_missed(reminder['id'])
            self.refresh_reminders()
        except Exception:
            pass


class AddReminderDialog:
    """Dialog for adding/editing reminders"""
    
    def __init__(self, parent, db_manager, callback, reminder=None, selected_date: date = None, auth_manager=None):
        self.db_manager = db_manager
        self.callback = callback
        self.reminder = reminder
        self.auth_manager = auth_manager
        # If parent view supplied a selected date, use it as the start date for new reminders
        self.selected_date = selected_date
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Reminder" if not reminder else "Edit Reminder")
        self.dialog.geometry("550x600")
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
        
        # Removed Time of Day section; infer slot based on time for display consistency
        self.time_slot_var = tk.StringVar(value="Custom")
        
        # Form fields
        fields_frame = tk.Frame(main_frame, bg='#f0f0f0')
        fields_frame.pack(fill=tk.BOTH, expand=True)
        
        # Patient selection
        self.create_field(fields_frame, "Patient:", "patient", "Aditya")
        
        # Number of days
        self.create_field(fields_frame, "Number of Days:", "days", "7")
        
        # Select time (flexible)
        self.create_field(fields_frame, "Select Time:", "time", "08:00 am")

        # Weekday selection
        weekday_frame = tk.Frame(fields_frame, bg='#f0f0f0')
        weekday_frame.pack(fill=tk.X, pady=5)
        tk.Label(weekday_frame, text="Repeat on days:", font=('Arial', 10, 'bold'), 
                 fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        self.weekday_vars = []  # 0=Mon .. 6=Sun
        days_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        days_container = tk.Frame(weekday_frame, bg='#f0f0f0')
        days_container.pack(anchor=tk.W, pady=(2, 0))
        for i, lbl in enumerate(days_labels):
            var = tk.BooleanVar(value=False)
            cb = tk.Checkbutton(days_container, text=lbl, variable=var, bg='#f0f0f0')
            cb.pack(side=tk.LEFT, padx=(0, 6))
            self.weekday_vars.append(var)
        
        # Medicine name
        self.create_field(fields_frame, "For which medicine?:", "medicine", "Enter Medicine name")
        
        # Select dose
        self.create_field(fields_frame, "Select Dose:", "dose", "1x")
        
        # Upload image section
        image_frame = tk.Frame(fields_frame, bg='#E8F5E8', relief=tk.RAISED, bd=1)
        image_frame.pack(fill=tk.X, pady=10)
        
        def show_wip_message():
            messagebox.showinfo("Coming Soon", "Image upload feature is work in progress!")
        
        image_btn = tk.Button(image_frame, text="📷 Upload Medicine Image", 
                            font=('Arial', 12), fg='#4CAF50', bg='#E8F5E8',
                            command=show_wip_message, relief=tk.FLAT)
        image_btn.pack(pady=20)
        
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
            # Patient dropdown - show only current user and their family members
            if self.auth_manager and self.auth_manager.get_current_user():
                cur = self.auth_manager.get_current_user()
                users = self.db_manager.get_users(owner_id=cur['id'])
                user_names = [u['name'] for u in users]
                default = cur['name']
            else:
                # Fallback for legacy behavior
                users = self.db_manager.get_users()
                user_names = [u['name'] for u in users]
                default = user_names[0] if user_names else "Aditya"

            var = tk.StringVar(value=default)
            dropdown = ttk.Combobox(field_frame, textvariable=var, values=user_names, 
                                   state="readonly", font=('Arial', 10))
            dropdown.pack(fill=tk.X, pady=(2, 0))
            setattr(self, f"{field_name}_var", var)
            
        elif field_name == "time":
            # Flexible time entry (12/24h)
            var = tk.StringVar(value=placeholder)
            entry = tk.Entry(field_frame, textvariable=var, font=('Arial', 10), 
                            relief=tk.FLAT, bd=1, bg='white')
            entry.pack(fill=tk.X, pady=(2, 0))
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
        # Load weekday selections
        days = self.reminder.get('days_of_week') if isinstance(self.reminder, dict) else None
        if days and hasattr(self, 'weekday_vars'):
            try:
                allowed = {int(x.strip()) for x in days.split(',') if x.strip() != ''}
                for i in range(min(7, len(self.weekday_vars))):
                    self.weekday_vars[i].set(i in allowed)
            except Exception:
                pass
    
    def save_reminder(self):
        """Save the reminder"""
        try:
            # Get form data
            time_slot = self.time_slot_var.get() or "Custom"
            patient_name = self.patient_var.get()
            days = int(self.days_var.get())
            specific_time = self.parse_time_to_24h(self.time_var.get())
            medicine_name = self.medicine_var.get()
            dose = self.dose_var.get()
            
            # Validate
            if not medicine_name.strip():
                messagebox.showerror("Error", "Please enter medicine name")
                return
            
            # Get user ID
            # Get current user's family members only
            current_user = self.auth_manager.get_current_user()
            if not current_user:
                messagebox.showerror("Error", "Not logged in")
                return
                
            users = self.db_manager.get_users(owner_id=current_user['id'])
            user = next((u for u in users if u['name'] == patient_name), None)
            if not user:
                messagebox.showerror("Error", "Invalid patient selected")
                return

            # Permission: if auth_manager exists, ensure current user can assign to this patient
            if hasattr(self, 'auth_manager') and self.auth_manager and self.auth_manager.get_current_user():
                cur = self.auth_manager.get_current_user()
                # Allow creating reminders only for self or family members (where current user is the owner)
                if user['id'] != cur['id'] and user.get('owner_id') != cur['id']:
                    messagebox.showerror("Permission denied", "You can only create reminders for yourself and your family members.")
                    return
            
            # Calculate dates
            start_date = self.selected_date or date.today()
            end_date = start_date + timedelta(days=days-1)
            
            # Days of week to persist
            selected_days = [str(i) for i, var in enumerate(self.weekday_vars) if var.get()] if hasattr(self, 'weekday_vars') else []
            days_of_week_str = ",".join(selected_days) if selected_days else None

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
                    take_with_food=True,
                    days_of_week=days_of_week_str
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
                    specific_time, start_date, end_date, True, None, days_of_week_str
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

    def parse_time_to_24h(self, value: str) -> str:
        """Parse flexible time strings to HH:MM (24h). Accepts '08:00', '8:00 am', '12:39AM'."""
        val = (value or '').strip().lower().replace('.', '')
        val = ' '.join(val.split())
        fmts = ['%H:%M', '%I:%M %p', '%I:%M%p', '%H%M']
        last_err = None
        for fmt in fmts:
            try:
                dt = datetime.strptime(val, fmt)
                return dt.strftime('%H:%M')
            except Exception as ex:
                last_err = ex
        import re
        m = re.match(r'^(\d{1,2})(\d{2})(am|pm)$', val)
        if m:
            h, mnt, ap = m.groups()
            dt = datetime.strptime(f"{h}:{mnt} {ap}", '%I:%M %p')
            return dt.strftime('%H:%M')
        raise ValueError(f"Invalid time format: '{value}'. Use HH:MM or h:MM am/pm")


class SettingsDialog:
    """Settings dialog"""
    
    def __init__(self, parent, notification_manager, auth_manager):
        self.notification_manager = notification_manager
        self.auth_manager = auth_manager
        
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
        
        # User info
        user_frame = tk.Frame(main_frame, bg='#f0f0f0')
        user_frame.pack(fill=tk.X, pady=10)
        tk.Label(user_frame, text="User Account", font=('Arial', 12, 'bold'), fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        current_user = self.auth_manager.get_current_user()
        if current_user:
            user_info_label = tk.Label(user_frame, text=f"Logged in as: {current_user['name']}", font=('Arial', 10), fg='#666666', bg='#f0f0f0')
            user_info_label.pack(anchor=tk.W, pady=(2, 5))
        # Account buttons
        account_btn_frame = tk.Frame(user_frame, bg='#f0f0f0')
        account_btn_frame.pack(fill=tk.X, pady=5)
        change_password_btn = tk.Button(account_btn_frame, text="Change Password", font=('Arial', 10), bg='#2196F3', fg='white', command=self.change_password, relief=tk.FLAT, padx=15, pady=5)
        change_password_btn.pack(side=tk.LEFT, padx=(0, 10))
        change_username_btn = tk.Button(account_btn_frame, text="Change Username", font=('Arial', 10), bg='#4CAF50', fg='white', command=self.change_username, relief=tk.FLAT, padx=15, pady=5)
        change_username_btn.pack(side=tk.LEFT, padx=(0, 10))
        logout_btn = tk.Button(account_btn_frame, text="Logout", font=('Arial', 10), bg='#F44336', fg='white', command=self.logout, relief=tk.FLAT, padx=15, pady=5)
        logout_btn.pack(side=tk.LEFT)
    def change_username(self):
        """Change username dialog"""
        change_dialog = tk.Toplevel(self.dialog)
        change_dialog.title("Change Username")
        change_dialog.geometry("300x200")
        change_dialog.configure(bg='#f0f0f0')
        change_dialog.transient(self.dialog)
        change_dialog.grab_set()
        
        main = tk.Frame(change_dialog, bg='#f0f0f0')
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        tk.Label(main, text="New Username:", font=('Arial', 10, 'bold'), fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        username_var = tk.StringVar()
        tk.Entry(main, textvariable=username_var, font=('Arial', 11), relief=tk.FLAT, bd=1, bg='white').pack(fill=tk.X, pady=(2, 15))
        
        def save():
            new_username = username_var.get().strip()
            if not new_username:
                messagebox.showerror("Error", "Please enter a username")
                return
            user = self.auth_manager.get_current_user()
            if user and self.db_manager.update_user_username(user['id'], new_username):
                messagebox.showinfo("Success", "Username updated successfully!")
                change_dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to update username")
        
        tk.Button(main, text="Save", font=('Arial', 12, 'bold'), bg='#4CAF50', fg='white', 
                  command=save, relief=tk.FLAT, padx=20, pady=8).pack(side=tk.BOTTOM)
    
    def create_settings(self):
        """Create settings interface"""
        main_frame = tk.Frame(self.dialog, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        title_label = tk.Label(main_frame, text="Settings", font=('Arial', 16, 'bold'), fg='#333333', bg='#f0f0f0')
        title_label.pack(pady=(0, 20))

        # User info
        user_frame = tk.Frame(main_frame, bg='#f0f0f0')
        user_frame.pack(fill=tk.X, pady=10)
        tk.Label(user_frame, text="User Account", font=('Arial', 12, 'bold'), fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        current_user = self.auth_manager.get_current_user()
        if current_user:
            user_info_label = tk.Label(user_frame, text=f"Logged in as: {current_user['name']}", font=('Arial', 10), fg='#666666', bg='#f0f0f0')
            user_info_label.pack(anchor=tk.W, pady=(2, 5))
        # Account buttons
        account_btn_frame = tk.Frame(user_frame, bg='#f0f0f0')
        account_btn_frame.pack(fill=tk.X, pady=5)
        change_password_btn = tk.Button(account_btn_frame, text="Change Password", font=('Arial', 10), bg='#2196F3', fg='white', command=self.change_password, relief=tk.FLAT, padx=15, pady=5)
        change_password_btn.pack(side=tk.LEFT, padx=(0, 10))
        change_username_btn = tk.Button(account_btn_frame, text="Change Username", font=('Arial', 10), bg='#4CAF50', fg='white', command=self.change_username, relief=tk.FLAT, padx=15, pady=5)
        change_username_btn.pack(side=tk.LEFT, padx=(0, 10))
        logout_btn = tk.Button(account_btn_frame, text="Logout", font=('Arial', 10), bg='#F44336', fg='white', command=self.logout, relief=tk.FLAT, padx=15, pady=5)
        logout_btn.pack(side=tk.LEFT)

        # Notification settings
        notif_frame = tk.Frame(main_frame, bg='#f0f0f0')
        notif_frame.pack(fill=tk.X, pady=10)
        tk.Label(notif_frame, text="Notifications", font=('Arial', 12, 'bold'), fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        test_btn = tk.Button(notif_frame, text="Test Notification", font=('Arial', 10), bg='#4CAF50', fg='white', command=self.test_notification, relief=tk.FLAT, padx=15, pady=5)
        test_btn.pack(anchor=tk.W, pady=(5, 0))

        # Close button
        close_btn = tk.Button(main_frame, text="Close", font=('Arial', 12), bg='#E0E0E0', fg='#666666', command=self.dialog.destroy, relief=tk.FLAT, padx=20, pady=10)
        close_btn.pack(side=tk.BOTTOM, pady=(20, 0))
    
    def test_notification(self):
        """Test notification"""
        self.notification_manager.send_test_notification()
    
    def change_password(self):
        """Open change password dialog"""
        ChangePasswordDialog(self.dialog, self.auth_manager)
    
    def logout(self):
        """Logout current user and exit application"""
        if messagebox.askyesno("Exit Application", "Are you sure you want to exit the application?"):
            self.auth_manager.logout()  # This will exit the application


class FamilyDialog:
    """Manage family members (add/remove)"""
    def __init__(self, parent, db_manager: DatabaseManager, on_change_callback=None, auth_manager=None):
        self.db_manager = db_manager
        self.auth_manager = auth_manager
        self.on_change_callback = on_change_callback
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Family Members")
        self.dialog.geometry("420x360")
        self.dialog.configure(bg='#f0f0f0')
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
        
        main = tk.Frame(self.dialog, bg='#f0f0f0')
        main.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)


        # Only allow logged-in user to manage their own family
        current_user = self.auth_manager.get_current_user() if self.auth_manager else None
        self.owner_id = current_user['id'] if current_user else None
        owner_name = current_user['name'] if current_user else ""
        tk.Label(main, text=f"Owner: {owner_name}", font=('Arial', 10, 'bold'), fg='#333333', bg='#f0f0f0').pack(anchor=tk.W, pady=(0,2))

        tk.Label(main, text="Add a family member:", font=('Arial', 12, 'bold'), fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        self.name_var = tk.StringVar()
        entry = tk.Entry(main, textvariable=self.name_var, font=('Arial', 11), relief=tk.FLAT, bd=1, bg='white')
        entry.pack(fill=tk.X, pady=(6, 10))

        btn_row = tk.Frame(main, bg='#f0f0f0')
        btn_row.pack(fill=tk.X)
        def add_member():
            name = (self.name_var.get() or '').strip()
            if not name:
                messagebox.showerror("Error", "Please enter a name")
                return
            # Only allow adding for self
            if not self.owner_id:
                messagebox.showerror("Error", "No owner selected")
                return
            try:
                new_id = self.db_manager.add_user(name, username=None, password=None, owner_id=self.owner_id, is_profile=True)
                self.name_var.set("")
                self.refresh_list()
                if self.on_change_callback:
                    self.on_change_callback()
                messagebox.showinfo("Success", f"Added {name} as family member.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add member: {e}")
        add_btn = tk.Button(btn_row, text="Add", font=('Arial', 10), bg='#4CAF50', fg='white', command=add_member, relief=tk.FLAT, padx=12, pady=4)
        add_btn.pack(side=tk.LEFT)

        def remove_selected():
            sel = self.members_list.curselection()
            if not sel:
                return
            index = sel[0]
            # Only consider the current user's family members here
            current_user = None
            if self.auth_manager:
                current_user = self.auth_manager.get_current_user()
            if current_user:
                users = self.db_manager.get_users(owner_id=current_user['id'])
            else:
                users = self.db_manager.get_users()
            # Map listbox index to users excluding adornments
            target_label = self.members_list.get(index)
            target_name = target_label.replace(" (You)", "")
            user = next((u for u in users if u['name'] == target_name), None)
            if not user:
                return
            if user['is_self']:
                messagebox.showerror("Error", "Cannot remove the main user")
                return
            if messagebox.askyesno("Confirm", f"Remove {user['name']} and their reminders?"):
                try:
                    self.db_manager.delete_user(user['id'])
                    self.refresh_list()
                    if self.on_change_callback:
                        self.on_change_callback()
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to remove member: {e}")
        remove_btn = tk.Button(btn_row, text="Remove", font=('Arial', 10), bg='#F44336', fg='white', command=remove_selected, relief=tk.FLAT, padx=12, pady=4)
        remove_btn.pack(side=tk.LEFT, padx=(8,0))
        
        # Members list
        tk.Label(main, text="Members:", font=('Arial', 12, 'bold'), fg='#333333', bg='#f0f0f0').pack(anchor=tk.W, pady=(12, 4))
        self.members_list = tk.Listbox(main, font=('Arial', 11))
        self.members_list.pack(fill=tk.BOTH, expand=True)
        
        self.refresh_list()
    
    def refresh_list(self):
        self.members_list.delete(0, tk.END)
        # Show only family members for logged-in user
        if not self.owner_id:
            return
        users = self.db_manager.get_users(owner_id=self.owner_id)
        for u in users:
            is_self = u['id'] == self.owner_id
            label = f"{u['name']}" + (" (Owner)" if is_self else "")
            self.members_list.insert(tk.END, label)


class HistoryDialog:
    """Display intake history with simple filters."""
    def __init__(self, parent, db_manager: DatabaseManager, auth_manager=None):
        self.db_manager = db_manager
        self.auth_manager = auth_manager
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Intake History")
        self.dialog.geometry("720x520")
        self.dialog.configure(bg='#f0f0f0')
        self.dialog.transient(parent)
        self.dialog.grab_set()
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 60, parent.winfo_rooty() + 60))
        
        main = tk.Frame(self.dialog, bg='#f0f0f0')
        main.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        
        # Filters row
        filters = tk.Frame(main, bg='#f0f0f0')
        filters.pack(fill=tk.X, pady=(0, 10))
        tk.Label(filters, text="User:", font=('Arial', 10, 'bold'), fg='#333333', bg='#f0f0f0').pack(side=tk.LEFT)
        # Only show current user and their family members in history
        current_user = None
        if self.auth_manager:
            current_user = self.auth_manager.get_current_user()
        users = []
        if current_user:
            users = self.db_manager.get_users(owner_id=current_user['id'])
        user_names = [u['name'] for u in users]
        self.user_filter_var = tk.StringVar(value="All")
        user_dropdown = ttk.Combobox(filters, textvariable=self.user_filter_var, values=["All"] + user_names, state="readonly", width=20)
        user_dropdown.pack(side=tk.LEFT, padx=(6, 20))

        tk.Label(filters, text="From:", font=('Arial', 10, 'bold'), fg='#333333', bg='#f0f0f0').pack(side=tk.LEFT)
        self.from_var = tk.StringVar(value=date.today().strftime('%Y-%m-01'))
        from_entry = tk.Entry(filters, textvariable=self.from_var, width=12)
        from_entry.pack(side=tk.LEFT, padx=(6, 12))
        tk.Label(filters, text="To:", font=('Arial', 10, 'bold'), fg='#333333', bg='#f0f0f0').pack(side=tk.LEFT)
        self.to_var = tk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        to_entry = tk.Entry(filters, textvariable=self.to_var, width=12)
        to_entry.pack(side=tk.LEFT, padx=(6, 12))

        btns = tk.Frame(filters, bg='#f0f0f0')
        btns.pack(side=tk.LEFT, padx=(10,0))
        refresh_btn = tk.Button(btns, text="Refresh", font=('Arial', 10), bg='#4CAF50', fg='white', relief=tk.FLAT, padx=10, command=self.refresh_table)
        refresh_btn.pack(side=tk.LEFT)
        delete_btn = tk.Button(btns, text="Delete Selected", font=('Arial', 10), bg='#F44336', fg='white', relief=tk.FLAT, padx=10, command=self.delete_selected)
        delete_btn.pack(side=tk.LEFT, padx=(8,0))
        clear_btn = tk.Button(btns, text="Clear Filtered", font=('Arial', 10), bg='#9E9E9E', fg='white', relief=tk.FLAT, padx=10, command=self.clear_filtered)
        clear_btn.pack(side=tk.LEFT, padx=(8,0))
        
        # Table
        columns = ("date", "time", "user", "medicine", "dose", "scheduled", "status")
        self.tree = ttk.Treeview(main, columns=columns, show='headings')
        for col, text in zip(columns, ["Date", "Time", "User", "Medicine", "Dose", "Scheduled", "Status"]):
            self.tree.heading(col, text=text)
            self.tree.column(col, width=100, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.refresh_table()
    
    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        # Parse filters
        start = self.from_var.get().strip()
        end = self.to_var.get().strip()
        start_date = datetime.strptime(start, '%Y-%m-%d').date() if start else None
        end_date = datetime.strptime(end, '%Y-%m-%d').date() if end else None
        user_name = self.user_filter_var.get()
        # Only show logs for current user and their family members
        current_user = None
        if hasattr(self, 'auth_manager') and self.auth_manager:
            current_user = self.auth_manager.get_current_user()
        users = []
        if current_user:
            users = self.db_manager.get_users(owner_id=current_user['id'])
        user_map = {u['name']: u['id'] for u in users}
        user_id = user_map.get(user_name) if user_name and user_name != "All" else None
        logs = self.db_manager.get_intake_logs(start_date, end_date, user_id)
        # Filter logs to only those for allowed users
        allowed_user_ids = set(user_map.values())
        logs = [l for l in logs if l['user_name'] in user_map]
        for l in logs:
            # Format time nicely
            time_text = ''
            if l['taken_at']:
                try:
                    time_text = datetime.strptime(l['taken_at'], '%Y-%m-%d %H:%M:%S').strftime('%I:%M %p').lower()
                except Exception:
                    time_text = l['taken_at']
            self.tree.insert('', tk.END, values=(
                l['intake_date'],
                time_text,
                l['user_name'],
                l['medicine_name'],
                l['dose'],
                l['specific_time'],
                l['status']
            ))

    def _current_filters(self):
        start = self.from_var.get().strip()
        end = self.to_var.get().strip()
        start_date = datetime.strptime(start, '%Y-%m-%d').date() if start else None
        end_date = datetime.strptime(end, '%Y-%m-%d').date() if end else None
        user_name = self.user_filter_var.get()
        # Respect current user's owner/family scope when available
        current_user = None
        if hasattr(self, 'auth_manager') and self.auth_manager:
            current_user = self.auth_manager.get_current_user()
        if current_user:
            users_list = self.db_manager.get_users(owner_id=current_user['id'])
        else:
            users_list = self.db_manager.get_users()
        users = {u['name']: u['id'] for u in users_list}
        user_id = users.get(user_name) if user_name and user_name != "All" else None
        return start_date, end_date, user_id

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        # Map selected to underlying log ids by refetching with filters and aligning rows
        start_date, end_date, user_id = self._current_filters()
        logs = self.db_manager.get_intake_logs(start_date, end_date, user_id)
        indices = [self.tree.index(i) for i in sel]
        indices.sort(reverse=True)
        for idx in indices:
            if 0 <= idx < len(logs):
                self.db_manager.delete_intake_log(logs[idx]['id'])
        self.refresh_table()

    def clear_filtered(self):
        start_date, end_date, user_id = self._current_filters()
        deleted = self.db_manager.clear_intake_logs(start_date, end_date, user_id)
        self.refresh_table()


def main():
    """Main function"""
    root = tk.Tk()
    app = MedicineReminderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
