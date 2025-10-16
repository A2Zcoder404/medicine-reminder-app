"""
Database module for Medicine Reminder App
Handles SQLite database operations for reminders and users
"""

import sqlite3
import os
from datetime import datetime, date, timedelta, timezone
try:
    from cryptography.fernet import Fernet
except Exception:
    Fernet = None
from typing import List, Dict, Optional, Tuple
from logging_config import logger

# Add custom date adapter for SQLite
def adapt_date(val):
    return val.isoformat()

def convert_date(val):
    return date.fromisoformat(val.decode())

# Register the adapters
sqlite3.register_adapter(date, adapt_date)
sqlite3.register_converter("date", convert_date)


class DatabaseManager:
    def update_user_username(self, user_id: int, new_username: str) -> bool:
        """Update a user's username"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET username = ? WHERE id = ?', (new_username, user_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    def __init__(self, db_path: str = None):
        # By default place the DB next to this module so it's stable across working directories
        if not db_path:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, 'medicine_reminders.db')
        self.db_path = db_path
        # Load/create encryption key for field-level encryption
        self._key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'secret.key')
        self._fernet = self._load_or_create_key()

        self.init_database()
        self._run_migrations()

    def _load_or_create_key(self) -> Fernet:
        """Load or create a Fernet key stored next to the package."""
        try:
            if Fernet is None:
                # cryptography not installed; return a no-op fernet-like object
                class _Noop:
                    def encrypt(self, b):
                        return b
                    def decrypt(self, b):
                        return b
                return _Noop()
            if os.path.exists(self._key_path):
                with open(self._key_path, 'rb') as f:
                    key = f.read()
            else:
                key = Fernet.generate_key()
                with open(self._key_path, 'wb') as f:
                    f.write(key)
            return Fernet(key)
        except Exception:
            # In the unlikely case key handling fails, fall back to a non-encrypting stub
            class _Noop:
                def encrypt(self, b):
                    return b
                def decrypt(self, b):
                    return b
            return _Noop()

    def _encrypt_field(self, value: str) -> str:
        if value is None:
            return None
        try:
            token = self._fernet.encrypt(value.encode('utf-8'))
            return token.decode('utf-8')
        except Exception:
            return value

    def _decrypt_field(self, token: str) -> str:
        if token is None:
            return None
        try:
            b = token.encode('utf-8')
            val = self._fernet.decrypt(b)
            return val.decode('utf-8')
        except Exception:
            return token
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT UNIQUE,
                password_hash TEXT,
                is_self BOOLEAN DEFAULT 0,
                owner_id INTEGER, -- owner account if this user is a family member
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_profile BOOLEAN DEFAULT 0
            )
        ''')
        
        # Create reminders table with encrypted fields for privacy
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
                days_of_week TEXT,
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
            # Create a default self user with username and password
            import bcrypt
            default_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute('INSERT INTO users (name, username, password_hash, is_self) VALUES (?, ?, ?, ?)',
                           ('Aditya', 'admin', default_password, 1))
        
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
        
        # Add authentication columns if missing and modify constraints
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [row[1] for row in cursor.fetchall()]
        
        # Create a new table with updated schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                username TEXT UNIQUE,
                password_hash TEXT,
                is_self BOOLEAN DEFAULT 0,
                owner_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_profile INTEGER DEFAULT 0
            )
        ''')
        
        # Copy data from old table to new table
        cursor.execute('INSERT OR IGNORE INTO users_new SELECT * FROM users')
        
        # Drop old table and rename new table
        cursor.execute('DROP TABLE IF EXISTS users')
        cursor.execute('ALTER TABLE users_new RENAME TO users')
        
        # Create default user with authentication if no users exist
        cursor.execute('SELECT COUNT(*) FROM users')
        if cursor.fetchone()[0] == 0:
            import bcrypt
            default_password = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute('INSERT INTO users (name, username, password_hash, is_self) VALUES (?, ?, ?, ?)', 
                         ('Admin', 'admin', default_password, 1))
        
        # Update existing users without authentication to have default credentials
        cursor.execute('SELECT id, name FROM users WHERE username IS NULL OR password_hash IS NULL')
        users_to_update = cursor.fetchall()
        for user_id, name in users_to_update:
            import bcrypt
            username = name.lower().replace(' ', '')
            default_password = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute('UPDATE users SET username = ?, password_hash = ? WHERE id = ?', 
                         (username, default_password, user_id))
        
        conn.commit()
        conn.close()

    def add_user(self, name: str, username: str = None, password: str = None, owner_id: int = None, is_self: bool = False, is_profile: bool = False) -> int:
        """Add a new user and return user ID. owner_id indicates this user belongs to another user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # For family profiles, do not set username/password
                if is_profile:
                    username = None
                    password_hash = None
                else:
                    # Generate default username and password if not provided
                    if not username:
                        username = name.lower().replace(' ', '')
                    if not password:
                        password = 'password123'
                    import bcrypt
                    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

                cursor.execute('INSERT INTO users (name, username, password_hash, is_self, owner_id, is_profile) VALUES (?, ?, ?, ?, ?, ?)', 
                             (name, username, password_hash, int(is_self), owner_id, int(bool(is_profile))) )
                user_id = cursor.lastrowid
                conn.commit()
                return user_id
        except sqlite3.Error as e:
            logger.error(f"Database error adding user: {e}")
            raise
    
    def get_users(self, owner_id: Optional[int] = None) -> List[Dict]:
        """Get users filtered by owner_id if provided.
        If owner_id is provided, returns only that user and their family members.
        If owner_id is None, returns all users (admin/legacy behavior).
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if owner_id is not None:
            # Return the owner and their family members
            cursor.execute('''
                SELECT id, name, username, is_self, owner_id 
                FROM users 
                WHERE id = ? OR owner_id = ?
                ORDER BY is_self DESC, name
            ''', (owner_id, owner_id))
        else:
            # Return all users (legacy/admin behavior)
            cursor.execute('''
                SELECT id, name, username, is_self, owner_id 
                FROM users 
                ORDER BY is_self DESC, name
            ''')
        users = [{'id': row[0], 'name': row[1], 'username': row[2], 'is_self': bool(row[3]), 'owner_id': row[4]} 
                for row in cursor.fetchall()]
        conn.close()
        return users

    def get_users_for_owner(self, owner_id: int) -> List[Dict]:
        """Return the owner (primary user) and their family members.
        Includes the owner row and any users whose owner_id matches.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, username, is_self, owner_id FROM users WHERE id = ? OR owner_id = ? ORDER BY is_self DESC, name', (owner_id, owner_id))
        users = [{'id': row[0], 'name': row[1], 'username': row[2], 'is_self': bool(row[3]), 'owner_id': row[4]} for row in cursor.fetchall()]
        conn.close()
        return users
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user with username and password"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, username, password_hash, is_self, is_profile FROM users WHERE username = ?', (username,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            import bcrypt
            user_id, name, db_username, password_hash, is_self, is_profile = row
            # Profiles are non-login entries; do not allow authentication for profiles
            if is_profile:
                return None
            if bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8')):
                return {
                    'id': user_id,
                    'name': name,
                    'username': db_username,
                    'is_self': bool(is_self)
                }
        return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, username, is_self FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'username': row[2],
                'is_self': bool(row[3])
            }
        return None
    
    def change_password(self, user_id: int, new_password: str) -> bool:
        """Change user password"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        import bcrypt
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def add_reminder(self, user_id: int, medicine_name: str, dose: str, 
                    time_slot: str, specific_time: str, start_date: date, 
                    end_date: date, take_with_food: bool = True, 
                    medicine_image_path: str = None, days_of_week: str = None) -> int:
        """Add a new reminder and return reminder ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Encrypt sensitive fields before storage
        enc_med = self._encrypt_field(medicine_name)
        enc_dose = self._encrypt_field(dose)
        enc_spec_time = self._encrypt_field(specific_time)

        cursor.execute('''
            INSERT INTO reminders 
            (user_id, medicine_name, dose, time_slot, specific_time, 
             start_date, end_date, take_with_food, medicine_image_path, days_of_week)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, enc_med, enc_dose, time_slot, enc_spec_time, 
              start_date, end_date, take_with_food, medicine_image_path, days_of_week))
        reminder_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return reminder_id
    
    def get_reminders_for_date(self, target_date: date, user_id: Optional[int] = None, owner_id: Optional[int] = None) -> List[Dict]:
        """Get reminders for a specific date, optionally filtered by user.
        Explicitly select columns to avoid index errors when schema changes.
        owner_id must be provided to enforce data isolation.
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
        clauses = ["r.start_date <= ?", "r.end_date >= ?"]
        params = [target_date, target_date]
        if owner_id:
            # Always filter by owner to enforce data isolation
            clauses.append("(u.id = ? OR u.owner_id = ?)")
            params.extend([owner_id, owner_id])
            if user_id:
                # Additional filter for specific user within owner's family
                clauses.append("(r.user_id = ? AND (u.id = ? OR u.owner_id = ?))")
                params.extend([user_id, owner_id, owner_id])
        elif user_id:
            # No owner provided - only show user's own reminders
            clauses.append("r.user_id = ?")
            params.append(user_id)
        where_sql = "WHERE " + " AND ".join(clauses)
        query = base_select + where_sql + " ORDER BY r.specific_time, u.name"
        cursor.execute(query, params)
        reminders: List[Dict] = []
        for row in cursor.fetchall():
            reminders.append({
                'id': row[0],
                'user_id': row[1],
                'medicine_name': self._decrypt_field(row[2]),
                'dose': self._decrypt_field(row[3]),
                'time_slot': row[4],
                'specific_time': self._decrypt_field(row[5]),
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
        """Mark a reminder as taken for today only, and log to intake_logs."""
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        intake_date = now.date()
        taken_at_str = now.strftime('%Y-%m-%d %H:%M:%S')

        try:
            conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
            cursor = conn.cursor()

            # Verify reminder exists and get user_id
            cursor.execute('SELECT user_id FROM reminders WHERE id = ?', (reminder_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False
            user_id = row[0]

            # Check if there's already an entry for today
            cursor.execute('SELECT id, status FROM intake_logs WHERE reminder_id = ? AND intake_date = ?', (reminder_id, intake_date))
            existing = cursor.fetchone()
            if existing:
                # If an entry exists (missed/taken), update it to taken so user action always wins
                log_id, prev_status = existing
                cursor.execute('UPDATE intake_logs SET status = ?, taken_at = ?, user_id = ? WHERE id = ?',
                               ('taken', taken_at_str, user_id, log_id))
            else:
                # Insert intake log for today
                cursor.execute('''
                    INSERT INTO intake_logs (reminder_id, user_id, intake_date, status, taken_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (reminder_id, user_id, intake_date, 'taken', taken_at_str))

            # Update reminders table
            cursor.execute('UPDATE reminders SET is_taken = 1, taken_at = ? WHERE id = ?', (taken_at_str, reminder_id))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            # Print to console for easier debugging in GUI environments
            print(f"Error marking reminder as taken: {e}")
            if 'conn' in locals():
                try:
                    conn.close()
                except:
                    pass
            return False

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
                'medicine_name': self._decrypt_field(row[4]) if row[4] else None,
                'dose': self._decrypt_field(row[5]) if row[5] else None,
                'specific_time': self._decrypt_field(row[6]) if row[6] else None,
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
        """Mark a reminder as missed for today only, and log to intake_logs."""
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        intake_date = now.date()

        try:
            conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
            cursor = conn.cursor()

            cursor.execute('SELECT user_id FROM reminders WHERE id = ?', (reminder_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False
            user_id = row[0]

            # If already logged for today, do not add duplicate
            cursor.execute('SELECT id FROM intake_logs WHERE reminder_id = ? AND intake_date = ?', (reminder_id, intake_date))
            if cursor.fetchone():
                conn.close()
                return False

            cursor.execute('''
                INSERT INTO intake_logs (reminder_id, user_id, intake_date, status)
                VALUES (?, ?, ?, ?)
            ''', (reminder_id, user_id, intake_date, 'missed'))

            # Ensure reminder is not marked taken
            cursor.execute('UPDATE reminders SET is_taken = 0, taken_at = NULL WHERE id = ?', (reminder_id,))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            print(f"Database error marking missed: {e}")
            if 'conn' in locals():
                try:
                    conn.close()
                except:
                    pass
            return False

    def update_reminder(self, reminder_id: int, **kwargs) -> bool:
        """Update reminder fields"""
        if not kwargs:
            return False

        # Build dynamic update query
        set_clauses = []
        values = []
        for key, value in kwargs.items():
            if key in ['medicine_name', 'dose', 'time_slot', 'specific_time', 
                       'start_date', 'end_date', 'take_with_food', 'medicine_image_path', 'days_of_week', 'user_id']:
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

    def get_reminders_for_date_filtered_by_weekday(self, target_date: date, user_id: Optional[int] = None, owner_id: Optional[int] = None) -> List[Dict]:
        """Get reminders for a specific date filtered by the weekday restrictions (if any)."""
        reminders = self.get_reminders_for_date(target_date, user_id=user_id, owner_id=owner_id)
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
                'medicine_name': self._decrypt_field(row[2]),
                'dose': self._decrypt_field(row[3]),
                'time_slot': row[4],
                'specific_time': self._decrypt_field(row[5]),
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
