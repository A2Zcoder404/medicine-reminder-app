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
        self._run_migrations()
    
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

        # Create intake logs table (history of taken/missed per date)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS intake_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reminder_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                intake_date DATE NOT NULL,
                status TEXT NOT NULL, -- 'taken' | 'missed'
                taken_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reminder_id) REFERENCES reminders (id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Insert default user (self)
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_self = 1')
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO users (name, is_self) VALUES (?, ?)', ('Aditya', 1))
        
        conn.commit()
        conn.close()
    
    def _run_migrations(self):
        """Run lightweight migrations to evolve schema without data loss"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Add days_of_week column if missing (stores comma-separated weekday indices 0=Mon..6=Sun)
        cursor.execute("PRAGMA table_info(reminders)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'days_of_week' not in columns:
            cursor.execute('ALTER TABLE reminders ADD COLUMN days_of_week TEXT')
        # Ensure self user is named 'Aditya'
        cursor.execute('UPDATE users SET name = ? WHERE is_self = 1 AND name != ?', ('Aditya', 'Aditya'))
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
                    medicine_image_path: str = None, days_of_week: str = None) -> int:
        """Add a new reminder and return reminder ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reminders 
            (user_id, medicine_name, dose, time_slot, specific_time, 
             start_date, end_date, take_with_food, medicine_image_path, days_of_week)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, medicine_name, dose, time_slot, specific_time, 
              start_date, end_date, take_with_food, medicine_image_path, days_of_week))
        reminder_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return reminder_id
    
    def get_reminders_for_date(self, target_date: date, user_id: Optional[int] = None) -> List[Dict]:
        """Get reminders for a specific date, optionally filtered by user.
        Explicitly select columns to avoid index errors when schema changes.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        base_select = (
            "SELECT "
            "r.id, r.user_id, r.medicine_name, r.dose, r.time_slot, r.specific_time, "
            "r.start_date, r.end_date, r.take_with_food, r.medicine_image_path, "
            "r.is_taken, r.taken_at, r.created_at, r.days_of_week, u.name as user_name "
            "FROM reminders r JOIN users u ON r.user_id = u.id "
        )
        if user_id:
            query = base_select + "WHERE r.user_id = ? AND r.start_date <= ? AND r.end_date >= ? ORDER BY r.specific_time, u.name"
            params = (user_id, target_date, target_date)
        else:
            query = base_select + "WHERE r.start_date <= ? AND r.end_date >= ? ORDER BY r.specific_time, u.name"
            params = (target_date, target_date)
        cursor.execute(query, params)
        reminders: List[Dict] = []
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
                'days_of_week': row[13],
                'user_name': row[14]
            })
        conn.close()
        return reminders
    
    def mark_reminder_taken(self, reminder_id: int) -> bool:
        """Mark a reminder as taken"""
        # Use IST (UTC+5:30) for taken_at timestamp
        from datetime import timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        taken_at_str = datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE reminders 
            SET is_taken = 1, taken_at = ? 
            WHERE id = ?
        ''', (taken_at_str, reminder_id))
        success = cursor.rowcount > 0
        if success:
            # Insert intake log row for today
            cursor.execute('SELECT user_id FROM reminders WHERE id = ?', (reminder_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
                intake_date = datetime.now(ist).date()
                cursor.execute('''
                    INSERT INTO intake_logs (reminder_id, user_id, intake_date, status, taken_at)
                    VALUES (?, ?, ?, 'taken', ?)
                ''', (reminder_id, user_id, intake_date, taken_at_str))
        conn.commit()
        conn.close()
        return success

    def get_intake_logs(self, start_date: Optional[date] = None, end_date: Optional[date] = None, user_id: Optional[int] = None) -> List[Dict]:
        """Fetch intake logs joined with reminder and user info, newest first."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        clauses = []
        params: List = []
        if start_date:
            clauses.append("il.intake_date >= ?")
            params.append(start_date)
        if end_date:
            clauses.append("il.intake_date <= ?")
            params.append(end_date)
        if user_id:
            clauses.append("il.user_id = ?")
            params.append(user_id)
        where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f'''
            SELECT il.id, il.intake_date, il.status, il.taken_at,
                   r.medicine_name, r.dose, r.specific_time,
                   u.name as user_name
            FROM intake_logs il
            JOIN reminders r ON il.reminder_id = r.id
            JOIN users u ON il.user_id = u.id
            {where_sql}
            ORDER BY il.intake_date DESC, il.taken_at DESC
        '''
        cursor.execute(sql, params)
        results: List[Dict] = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'intake_date': row[1],
                'status': row[2],
                'taken_at': row[3],
                'medicine_name': row[4],
                'dose': row[5],
                'specific_time': row[6],
                'user_name': row[7],
            })
        conn.close()
        return results

    def delete_intake_log(self, log_id: int) -> bool:
        """Delete a single intake log record by id"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM intake_logs WHERE id = ?', (log_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def clear_intake_logs(self, start_date: Optional[date] = None, end_date: Optional[date] = None, user_id: Optional[int] = None) -> int:
        """Delete multiple intake logs by optional filters; returns deleted count"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        clauses = []
        params: List = []
        if start_date:
            clauses.append('intake_date >= ?')
            params.append(start_date)
        if end_date:
            clauses.append('intake_date <= ?')
            params.append(end_date)
        if user_id:
            clauses.append('user_id = ?')
            params.append(user_id)
        where_sql = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
        sql = f'DELETE FROM intake_logs {where_sql}'
        cursor.execute(sql, params)
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count
    
    def mark_reminder_missed(self, reminder_id: int) -> bool:
        """Mark a reminder as missed (not taken)"""
        from datetime import timezone, timedelta
        ist = timezone(timedelta(hours=5, minutes=30))
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE reminders 
            SET is_taken = 0, taken_at = NULL 
            WHERE id = ?
        ''', (reminder_id,))
        success = cursor.rowcount > 0
        if success:
            # Insert missed intake log row for today
            cursor.execute('SELECT user_id FROM reminders WHERE id = ?', (reminder_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
                intake_date = datetime.now(ist).date()
                cursor.execute('''
                    INSERT INTO intake_logs (reminder_id, user_id, intake_date, status)
                    VALUES (?, ?, ?, 'missed')
                ''', (reminder_id, user_id, intake_date))
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
                      'start_date', 'end_date', 'take_with_food', 'medicine_image_path', 'days_of_week']:
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

    def get_reminders_for_date_filtered_by_weekday(self, target_date: date, user_id: Optional[int] = None) -> List[Dict]:
        """Get reminders for a specific date filtered by the weekday restrictions (if any)."""
        reminders = self.get_reminders_for_date(target_date, user_id)
        weekday_index = target_date.weekday()  # 0=Mon .. 6=Sun
        filtered: List[Dict] = []
        for r in reminders:
            days = r.get('days_of_week')
            if not days or days.strip() == '':
                filtered.append(r)
                continue
            # Expect comma-separated numbers
            try:
                allowed = {int(x.strip()) for x in days.split(',') if x.strip() != ''}
                if weekday_index in allowed:
                    filtered.append(r)
            except Exception:
                # On malformed data, include by default
                filtered.append(r)
        return filtered

    def reset_daily_taken_flags(self, target_date: date):
        """Reset is_taken and taken_at for reminders active on target_date.
        This enables daily confirmation without persisting yesterday's taken state.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE reminders
            SET is_taken = 0, taken_at = NULL
            WHERE start_date <= ? AND end_date >= ?
        ''', (target_date, target_date))
        conn.commit()
        conn.close()
    
    def delete_reminder(self, reminder_id: int) -> bool:
        """Delete a reminder"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM reminders WHERE id = ?', (reminder_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def delete_user(self, user_id: int) -> bool:
        """Delete a user and their reminders. Prevent deletion of the self user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Check if self
        cursor.execute('SELECT is_self FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        if row[0]:
            conn.close()
            return False
        # Delete reminders then user
        cursor.execute('DELETE FROM reminders WHERE user_id = ?', (user_id,))
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def get_reminder_by_id(self, reminder_id: int) -> Optional[Dict]:
        """Get a specific reminder by ID with explicit column order"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.id, r.user_id, r.medicine_name, r.dose, r.time_slot, r.specific_time,
                   r.start_date, r.end_date, r.take_with_food, r.medicine_image_path,
                   r.is_taken, r.taken_at, r.created_at, r.days_of_week, u.name as user_name
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
                'days_of_week': row[13],
                'user_name': row[14]
            }
        return None
