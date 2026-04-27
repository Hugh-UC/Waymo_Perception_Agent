"""
File: auth_db.py
Title: User Authentication Database Tool
Description: Manages the secure creation, storage, and retrieval of user accounts, 
passwords (hashed), and role-based permissions in an isolated SQLite database.
Author: Hugh Brennan
Date: 2026-04-24
Version: 0.1
"""
import os
import sqlite3
import hashlib
from datetime import datetime
from typing import Any

# isolate user data from metrics data
DB_PATH : str = os.path.join("data", "users.db")

def _hash_password(password: str) -> str:
    """Creates a secure SHA-256 hash of the password."""
    return hashlib.sha256(password.encode()).hexdigest()

def init_user_db() -> None:
    """
    Creates the necessary tables for the user database if they do not exist.
    """
    os.makedirs("data", exist_ok=True)
    
    conn : sqlite3.Connection = sqlite3.connect(DB_PATH)
    cursor : sqlite3.Cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'viewer',
            job_title TEXT,
            created_at TEXT NOT NULL,
            last_login TEXT,
            two_factor_enabled BOOLEAN DEFAULT 0,
            two_factor_secret TEXT
        )
    ''')
    
    # secondary table to store specific overrides for 'custom' users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS custom_permissions (
            user_id INTEGER PRIMARY KEY,
            run_pipeline BOOLEAN,
            config_scopes TEXT,
            manage_users_scopes TEXT,
            view_metrics BOOLEAN,
            export_data BOOLEAN,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

def check_auth_setup() -> bool:
    """
    Checks if the user database exists and contains at least one registered administrator.
    Used by the FastAPI server to dictate Setup Wizard routing without exposing SQL logic.

    Returns:
        bool: True if database is healthy and has users, False otherwise.
    """
    if not os.path.exists(DB_PATH):
        return False
        
    try:
        conn : sqlite3.Connection = sqlite3.connect(DB_PATH)
        cursor : sqlite3.Cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")

        count : int = cursor.fetchone()[0]

        conn.close()
        return count > 0
    
    except sqlite3.OperationalError:
        return False
    
    except Exception as e:
        print(f"[Auth DB Error] Status check failed: {e}")
        return False

def repair_auth_tables() -> bool:
    """
    Attempts to auto-heal missing authentication tables. Designed to be called 
    by system_check.py if structural database anomalies are detected.

    Returns:
        bool: True if repair executes successfully, False otherwise.
    """
    try:
        init_user_db()
        return True
    
    except Exception as e:
        print(f"[Auth DB Error] Repair failed: {e}")
        return False

def create_user(username: str, email: str, password: str, role: str, job_title: str = "") -> bool:
    """
    Registers a new user in the database.
    
    Returns:
        bool: True if created successfully, False if username/email already exists.
    """
    init_user_db() # ensure DB exists
    
    try:
        conn : sqlite3.Connection = sqlite3.connect(DB_PATH)
        cursor : sqlite3.Cursor = conn.cursor()
        
        now : str = datetime.now().isoformat()
        hashed_pw : str = _hash_password(password)
        
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, role, job_title, created_at, two_factor_enabled)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        ''', (username, email, hashed_pw, role, job_title, now))
        
        conn.commit()
        conn.close()
        return True
    
    except sqlite3.IntegrityError:
        # triggers if username or email is not unique
        return False
    
    except Exception as e:
        print(f"[Auth DB Error] Failed to create user: {e}")
        return False
    
def verify_user(username: str, password: str) -> dict | None:
    """
    Verifies a user's login credentials and retrieves their profile.
    
    Returns:
        dict | None: The user's row as a dictionary if valid, None if invalid.
    """
    try:
        conn : sqlite3.Connection = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor : sqlite3.Cursor = conn.cursor()
        
        hashed_pw : str = _hash_password(password)
        cursor.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, hashed_pw))
        
        user = cursor.fetchone()
        
        # update last login time if successful
        if user:
            now : str = datetime.now().isoformat()
            cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user['id']))
            conn.commit()
            
        conn.close()
        
        return dict(user) if user else None
    
    except Exception as e:
        print(f"[Auth DB Error] Verification failed: {e}")
        return None
    
def get_all_users() -> list[dict[str, Any]]:
    """
    Retrieves all users from the database, excluding password hashes.

    Returns:
        list[dict[str, Any]]: list of dictionaries containing safe user data for frontend table.
    """
    try:
        conn : sqlite3.Connection = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor : sqlite3.Cursor = conn.cursor()
        
        # explicitly select columns to avoid returning password_hash
        cursor.execute("SELECT id, username, email, role, job_title, created_at, last_login, two_factor_enabled FROM users")
        users = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return users
    except Exception as e:
        print(f"[Auth DB Error] Failed to retrieve users: {e}")
        return []

def delete_user(user_id: int) -> bool:
    """
    Deletes a user from the database by their ID.

    Args:
        user_id (int): primary key ID of the user to remove.

    Returns:
        bool: True if the user was successfully deleted, False otherwise.
    """
    try:
        conn : sqlite3.Connection = sqlite3.connect(DB_PATH)
        cursor : sqlite3.Cursor = conn.cursor()
        
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[Auth DB Error] Failed to delete user: {e}")
        return False


if __name__ == "__main__":
    # test block to generate the DB and master admin account
    print("Initializing User Database...")
    init_user_db()
    print("Database created. Creating default Master Admin...")
    success = create_user("admin", "admin@waymo.com", "securepassword123", "admin", "System Administrator")
    if success:
        print("Master Admin created successfully.")
    else:
        print("Admin already exists or creation failed.")