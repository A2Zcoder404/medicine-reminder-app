"""
Database module for Medicine Reminder App
Handles SQLite database operations for reminders and users
"""

import sqlite3
import os
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple

class DatabaseManager:
    def __init__(self, db_path: str = "medicine_reminders.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_self BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create reminders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                medicine_name TEXT NOT NULL,
                dose TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                specific_time TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                take_with_food BOOLEAN DEFAULT 1,
                medicine_image_path TEXT,
                is_taken BOOLEAN DEFAULT 0,
                taken_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Insert default user (self)
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_self = 1')
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO users (name, is_self) VALUES (?, ?)', ('Myself', 1))
        
        conn.commit()
        conn.close()
    
    def add_user(self, name: str) -> int:
        """Add a new user and return user ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO users (name) VALUES (?)', (name,))
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    
    def get_users(self) -> List[Dict]:
        """Get all users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, is_self FROM users ORDER BY is_self DESC, name')
        users = [{'id': row[0], 'name': row[1], 'is_self': bool(row[2])} for row in cursor.fetchall()]
        conn.close()
        return users
    
    def add_reminder(self, user_id: int, medicine_name: str, dose: str, 
                    time_slot: str, specific_time: str, start_date: date, 
                    end_date: date, take_with_food: bool = True, 
                    medicine_image_path: str = None) -> int:
        """Add a new reminder and return reminder ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reminders 
            (user_id, medicine_name, dose, time_slot, specific_time, 
             start_date, end_date, take_with_food, medicine_image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, medicine_name, dose, time_slot, specific_time, 
              start_date, end_date, take_with_food, medicine_image_path))
        reminder_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return reminder_id
    
    def get_reminders_for_date(self, target_date: date, user_id: Optional[int] = None) -> List[Dict]:
        """Get reminders for a specific date, optionally filtered by user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('''
                SELECT r.*, u.name as user_name
                FROM reminders r
                JOIN users u ON r.user_id = u.id
                WHERE r.user_id = ? AND r.start_date <= ? AND r.end_date >= ?
                ORDER BY r.specific_time, u.name
            ''', (user_id, target_date, target_date))
        else:
            cursor.execute('''
                SELECT r.*, u.name as user_name
                FROM reminders r
                JOIN users u ON r.user_id = u.id
                WHERE r.start_date <= ? AND r.end_date >= ?
                ORDER BY r.specific_time, u.name
            ''', (target_date, target_date))
        
        reminders = []
        for row in cursor.fetchall():
            reminders.append({
                'id': row[0],
                'user_id': row[1],
                'medicine_name': row[2],
                'dose': row[3],
                'time_slot': row[4],
                'specific_time': row[5],
                'start_date': row[6],
                'end_date': row[7],
                'take_with_food': bool(row[8]),
                'medicine_image_path': row[9],
                'is_taken': bool(row[10]),
                'taken_at': row[11],
                'created_at': row[12],
                'user_name': row[13]
            })
        
        conn.close()
        return reminders
    
    def mark_reminder_taken(self, reminder_id: int) -> bool:
        """Mark a reminder as taken"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE reminders 
            SET is_taken = 1, taken_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (reminder_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def mark_reminder_missed(self, reminder_id: int) -> bool:
        """Mark a reminder as missed (not taken)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE reminders 
            SET is_taken = 0, taken_at = NULL 
            WHERE id = ?
        ''', (reminder_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def update_reminder(self, reminder_id: int, **kwargs) -> bool:
        """Update reminder fields"""
        if not kwargs:
            return False
        
        # Build dynamic update query
        set_clauses = []
        values = []
        for key, value in kwargs.items():
            if key in ['medicine_name', 'dose', 'time_slot', 'specific_time', 
                      'start_date', 'end_date', 'take_with_food', 'medicine_image_path']:
                set_clauses.append(f"{key} = ?")
                values.append(value)
        
        if not set_clauses:
            return False
        
        values.append(reminder_id)
        query = f"UPDATE reminders SET {', '.join(set_clauses)} WHERE id = ?"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(query, values)
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def delete_reminder(self, reminder_id: int) -> bool:
        """Delete a reminder"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def get_reminder_by_id(self, reminder_id: int) -> Optional[Dict]:
        """Get a specific reminder by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, u.name as user_name
            FROM reminders r
            JOIN users u ON r.user_id = u.id
            WHERE r.id = ?
        ''', (reminder_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'medicine_name': row[2],
                'dose': row[3],
                'time_slot': row[4],
                'specific_time': row[5],
                'start_date': row[6],
                'end_date': row[7],
                'take_with_food': bool(row[8]),
                'medicine_image_path': row[9],
                'is_taken': bool(row[10]),
                'taken_at': row[11],
                'created_at': row[12],
                'user_name': row[13]
            }
        return None
