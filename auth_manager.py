"""
Authentication Manager for Medicine Reminder App
Handles user login, logout, and session management
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict, Callable
from database import DatabaseManager

class AuthManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.current_user: Optional[Dict] = None
        self.on_login_callback: Optional[Callable] = None
        self.on_logout_callback: Optional[Callable] = None
    
    def set_login_callback(self, callback: Callable):
        """Set callback to be called when user logs in"""
        self.on_login_callback = callback
    
    def set_logout_callback(self, callback: Callable):
        """Set callback to be called when user logs out"""
        self.on_logout_callback = callback
    
    def is_logged_in(self) -> bool:
        """Check if user is currently logged in"""
        return self.current_user is not None
    
    def get_current_user(self) -> Optional[Dict]:
        """Get current logged-in user"""
        return self.current_user
    
    def login(self, username: str, password: str) -> bool:
        """Authenticate user and set current user"""
        user = self.db_manager.authenticate_user(username, password)
        if user:
            # Set current_user and mark as primary session user
            self.current_user = user
            if self.on_login_callback:
                self.on_login_callback(user)
            return True
        return False
    
    def logout(self):
        """Logout current user and exit application"""
        if self.current_user and self.on_logout_callback:
            self.on_logout_callback(self.current_user)
        self.current_user = None
        # Exit the application
        import sys
        sys.exit(0)
    
    def change_password(self, old_password: str, new_password: str) -> bool:
        """Change password for current user"""
        if not self.current_user:
            return False
        
        # Verify old password
        user = self.db_manager.authenticate_user(self.current_user['username'], old_password)
        if not user:
            return False
        
        # Change password
        return self.db_manager.change_password(self.current_user['id'], new_password)


class LoginDialog:
    """Login dialog for user authentication"""
    
    def __init__(self, parent, auth_manager: AuthManager, on_success_callback: Callable):
        self.auth_manager = auth_manager
        self.on_success_callback = on_success_callback
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Login - Medicine Reminder")
        self.dialog.geometry("400x400")
        self.dialog.configure(bg='#f0f0f0')
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
        
        # Make dialog modal
        self.dialog.focus_set()
        
        self.create_login_form()
    
    def create_login_form(self):
        """Create the login form"""
        main_frame = tk.Frame(self.dialog, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Title
        title_label = tk.Label(main_frame, text="🔐 Login", 
                              font=('Arial', 18, 'bold'), fg='#333333', bg='#f0f0f0')
        title_label.pack(pady=(0, 30))
        
        # Login form
        form_frame = tk.Frame(main_frame, bg='#f0f0f0')
        form_frame.pack(fill=tk.X, pady=10)
        
        # Username field
        username_frame = tk.Frame(form_frame, bg='#f0f0f0')
        username_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(username_frame, text="Username:", font=('Arial', 10, 'bold'), 
                fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        
        self.username_var = tk.StringVar()
        username_entry = tk.Entry(username_frame, textvariable=self.username_var, 
                                 font=('Arial', 11), relief=tk.FLAT, bd=1, bg='white')
        username_entry.pack(fill=tk.X, pady=(2, 0))
        
        # Password field
        password_frame = tk.Frame(form_frame, bg='#f0f0f0')
        password_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(password_frame, text="Password:", font=('Arial', 10, 'bold'), 
                fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        
        self.password_var = tk.StringVar()
        password_entry = tk.Entry(password_frame, textvariable=self.password_var, 
                                 font=('Arial', 11), relief=tk.FLAT, bd=1, bg='white', show='*')
        password_entry.pack(fill=tk.X, pady=(2, 0))
        
        # Default credentials info
        info_frame = tk.Frame(form_frame, bg='#E8F5E8', relief=tk.RAISED, bd=1)
        info_frame.pack(fill=tk.X, pady=15)
        
        info_label = tk.Label(info_frame, text="Default credentials:\nUsername: admin\nPassword: admin123", 
                            font=('Arial', 9), fg='#4CAF50', bg='#E8F5E8', justify=tk.LEFT)
        info_label.pack(pady=10)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        login_btn = tk.Button(button_frame, text="Login", 
                            font=('Arial', 12, 'bold'), bg='#4CAF50', fg='white',
                            command=self.attempt_login, relief=tk.FLAT, padx=20, pady=10)
        login_btn.pack(side=tk.RIGHT)
        # Bind Enter key to login
        self.dialog.bind('<Return>', lambda e: self.attempt_login())
        username_entry.focus_set()

        # Signup link/button
        signup_btn = tk.Button(button_frame, text="Sign up", 
                               font=('Arial', 11), bg='#E0E0E0', fg='#333333',
                               command=self.open_signup, relief=tk.FLAT, padx=12, pady=8)
        signup_btn.pack(side=tk.RIGHT, padx=(0, 10))
    
    def attempt_login(self):
        """Attempt to login with provided credentials"""
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return
        
        if self.auth_manager.login(username, password):
            messagebox.showinfo("Success", f"Welcome back, {self.auth_manager.current_user['name']}!")
            self.dialog.destroy()
            self.on_success_callback()
        else:
            messagebox.showerror("Error", "Invalid username or password")

    def open_signup(self):
        """Open the signup dialog"""
        SignupDialog(self.dialog, self.auth_manager)


class SignupDialog:
    """Dialog for new user signup"""
    def __init__(self, parent, auth_manager: AuthManager):
        self.auth_manager = auth_manager
        self.db = self.auth_manager.db_manager

        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Sign Up - Medicine Reminder")
        self.dialog.geometry("450x480")
        self.dialog.configure(bg='#f0f0f0')
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 120, parent.winfo_rooty() + 80))
        self.dialog.focus_set()

        self.create_signup_form()

    def create_signup_form(self):
        main_frame = tk.Frame(self.dialog, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

        title_label = tk.Label(main_frame, text="Create Account", 
                               font=('Arial', 18, 'bold'), fg='#333333', bg='#f0f0f0')
        title_label.pack(pady=(0, 20))

        form_frame = tk.Frame(main_frame, bg='#f0f0f0')
        form_frame.pack(fill=tk.X, pady=10)

        # Name
        tk.Label(form_frame, text="Full name:", font=('Arial', 10, 'bold'), 
                fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        self.name_var = tk.StringVar()
        name_entry = tk.Entry(form_frame, textvariable=self.name_var, font=('Arial', 11), bg='white')
        name_entry.pack(fill=tk.X, pady=(2,8))
        name_entry.focus_set()

        # Username
        tk.Label(form_frame, text="Username:", font=('Arial', 10, 'bold'), 
                fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        self.username_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.username_var, font=('Arial', 11), bg='white').pack(fill=tk.X, pady=(2,8))

        # Password
        tk.Label(form_frame, text="Password:", font=('Arial', 10, 'bold'), 
                fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        self.password_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.password_var, font=('Arial', 11), bg='white', show='*').pack(fill=tk.X, pady=(2,8))

        # Confirm password
        tk.Label(form_frame, text="Confirm Password:", font=('Arial', 10, 'bold'), 
                fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        self.confirm_var = tk.StringVar()
        tk.Entry(form_frame, textvariable=self.confirm_var, font=('Arial', 11), bg='white', show='*').pack(fill=tk.X, pady=(2,12))

        # Buttons
        button_frame = tk.Frame(main_frame, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, pady=(10, 0))

        create_btn = tk.Button(button_frame, text="Create Account", 
                               font=('Arial', 12, 'bold'), bg='#4CAF50', fg='white',
                               command=self.attempt_signup, relief=tk.FLAT, padx=20, pady=10)
        create_btn.pack(side=tk.RIGHT)

        cancel_btn = tk.Button(button_frame, text="Cancel", 
                               font=('Arial', 12), bg='#E0E0E0', fg='#666666',
                               command=self.dialog.destroy, relief=tk.FLAT, padx=12, pady=10)
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))

    def attempt_signup(self):
        name = self.name_var.get().strip()
        username = self.username_var.get().strip()
        password = self.password_var.get().strip()
        confirm = self.confirm_var.get().strip()

        if not all([name, username, password, confirm]):
            messagebox.showerror("Error", "Please fill in all fields")
            return

        if password != confirm:
            messagebox.showerror("Error", "Passwords do not match")
            return

        if len(password) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters long")
            return

        # Check for duplicate username
        existing = self.db.authenticate_user(username, password + "_CHECK")
        # Note: authenticate_user checks password; to detect duplicate username without correct password,
        # query DB directly
        conn = self.db.__class__(self.db.db_path) if False else None
        try:
            # Check for duplicate username across all users since usernames must be globally unique
            # This needs to check ALL users, not just family members
            users = self.db.get_users(owner_id=None)  # Get all users
            if any(u['username'] == username for u in users):
                messagebox.showerror("Error", "Username already exists")
                return
        except Exception:
            # Fallback: continue and let DB raise unique constraint
            pass

        try:
            # When a user signs up directly, they become a primary user (is_self=True)
            user_id = self.db.add_user(name=name, username=username, password=password, is_self=True)
            if user_id:
                messagebox.showinfo("Success", "Account created successfully. You can now log in.")
                self.dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to create account. Please try again.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create account: {e}")


class ChangePasswordDialog:
    """Dialog for changing password"""
    
    def __init__(self, parent, auth_manager: AuthManager):
        self.auth_manager = auth_manager
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Change Password")
        self.dialog.geometry("400x250")
        self.dialog.configure(bg='#f0f0f0')
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
        
        self.create_password_form()
    
    def create_password_form(self):
        """Create the password change form"""
        main_frame = tk.Frame(self.dialog, bg='#f0f0f0')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)
        
        # Title
        title_label = tk.Label(main_frame, text="Change Password", 
                              font=('Arial', 16, 'bold'), fg='#333333', bg='#f0f0f0')
        title_label.pack(pady=(0, 20))
        
        # Form fields
        form_frame = tk.Frame(main_frame, bg='#f0f0f0')
        form_frame.pack(fill=tk.X, pady=10)
        
        # Current password
        current_frame = tk.Frame(form_frame, bg='#f0f0f0')
        current_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(current_frame, text="Current Password:", font=('Arial', 10, 'bold'), 
                fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        
        self.current_password_var = tk.StringVar()
        current_entry = tk.Entry(current_frame, textvariable=self.current_password_var, 
                                font=('Arial', 11), relief=tk.FLAT, bd=1, bg='white', show='*')
        current_entry.pack(fill=tk.X, pady=(2, 0))
        
        # New password
        new_frame = tk.Frame(form_frame, bg='#f0f0f0')
        new_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(new_frame, text="New Password:", font=('Arial', 10, 'bold'), 
                fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        
        self.new_password_var = tk.StringVar()
        new_entry = tk.Entry(new_frame, textvariable=self.new_password_var, 
                            font=('Arial', 11), relief=tk.FLAT, bd=1, bg='white', show='*')
        new_entry.pack(fill=tk.X, pady=(2, 0))
        
        # Confirm password
        confirm_frame = tk.Frame(form_frame, bg='#f0f0f0')
        confirm_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(confirm_frame, text="Confirm New Password:", font=('Arial', 10, 'bold'), 
                fg='#333333', bg='#f0f0f0').pack(anchor=tk.W)
        
        self.confirm_password_var = tk.StringVar()
        confirm_entry = tk.Entry(confirm_frame, textvariable=self.confirm_password_var, 
                                font=('Arial', 11), relief=tk.FLAT, bd=1, bg='white', show='*')
        confirm_entry.pack(fill=tk.X, pady=(2, 0))
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='#f0f0f0')
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        change_btn = tk.Button(button_frame, text="Change Password", 
                             font=('Arial', 12, 'bold'), bg='#4CAF50', fg='white',
                             command=self.change_password, relief=tk.FLAT, padx=20, pady=10)
        change_btn.pack(side=tk.RIGHT)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", 
                             font=('Arial', 12), bg='#E0E0E0', fg='#666666',
                             command=self.dialog.destroy, relief=tk.FLAT, padx=20, pady=10)
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))
    
    def change_password(self):
        """Change the password"""
        current_password = self.current_password_var.get().strip()
        new_password = self.new_password_var.get().strip()
        confirm_password = self.confirm_password_var.get().strip()
        
        if not all([current_password, new_password, confirm_password]):
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        if new_password != confirm_password:
            messagebox.showerror("Error", "New passwords do not match")
            return
        
        if len(new_password) < 6:
            messagebox.showerror("Error", "Password must be at least 6 characters long")
            return
        
        if self.auth_manager.change_password(current_password, new_password):
            messagebox.showinfo("Success", "Password changed successfully!")
            self.dialog.destroy()
        else:
            messagebox.showerror("Error", "Invalid current password")
