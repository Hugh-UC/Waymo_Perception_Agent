"""
File: system_check.py
Title: System Integrity & Auto-Recovery Engine
Description: Validates the project's directory structure and core files at runtime. 
Automatically generates missing data directories and prompts the user to securely 
download missing source code files directly from the master GitHub repository.
Author: Hugh Brennan
Date: 2026-04-24
Version: 0.1
"""
import os
import sys
import time
import requests
from typing import List

# Package Imports
from tools.db import check_metrics_setup, repair_metrics_tables
from tools.auth_db import check_auth_setup, repair_auth_tables

# The raw content URL for your GitHub repository. 
# MUST END WITH A FORWARD SLASH. Update 'main' if your branch name is different.
GITHUB_RAW_BASE_URL : str = "https://raw.githubusercontent.com/Hugh-UC/Waymo_Perception_Agent/main/"

def _download_from_github(file_path: str, max_retries: int = 3) -> bool:
    """
    Attempts to download a specific file from the GitHub repository.

    Args:
        file_path (str): The relative local path of the file to download.
        max_retries (int): Number of connection attempts before failing gracefully.

    Returns:
        bool: True if download and save was successful, False otherwise.
    """
    # normalize windows backslashes to URL forward slashes
    url_path : str = file_path.replace("\\", "/")
    target_url : str = f"{GITHUB_RAW_BASE_URL}{url_path}"
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"  -> Pulling {file_path} (Attempt {attempt}/{max_retries})...")
            # 10-second timeout prevents program from hanging indefinitely
            response : requests.Response = requests.get(target_url, timeout=10)
            response.raise_for_status()
            
            # ensure local subdirectory exists before writing file
            os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)
            
            with open(file_path, "wb") as f:
                f.write(response.content)
            
            print(f"     ✅ Successfully restored {file_path}")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"     [Network Error] {e}")
            if attempt < max_retries:
                time.sleep(2) # wait 2 seconds before retrying
                
    return False

def verify_system_integrity() -> bool:
    """
    Checks the current working directory for required folders and core files.
    Automatically generates missing data directories. If core files are missing,
    prompts the user to initiate the auto-recovery download sequence.

    Returns:
        bool: True if the system is completely intact or successfully repaired, 
              False if critically damaged or user aborts recovery.
    """
    # 1. directories system needs to safely write data into
    required_dirs : List[str] = [
        "data",
        "config",
        os.path.join("exports", "csv"),
        os.path.join("exports", "graphs")
    ]
    
    # 2. comprehensive map of project's source code
    critical_files : List[str] = [
        "main.py",
        "requirements.txt",
        os.path.join("server", "app.py"),
        os.path.join("config", "models.base.json"),
        os.path.join("config", "roles.json"),
        os.path.join("config", "params.yaml"),
        os.path.join("config", "graphs.json"),
        os.path.join("core", "__init__.py"),
        os.path.join("core", "schema.py"),
        os.path.join("core", "agent.py"),
        os.path.join("core", "utils.py"),
        os.path.join("core", "system_check.py"),
        os.path.join("tools", "__init__.py"),
        os.path.join("tools", "scraper.py"),
        os.path.join("tools", "db.py"),
        os.path.join("tools", "auth_db.py"),
        os.path.join("tools", "export.py"),
        os.path.join("tools", "visualisation", "__init__.py"),
        os.path.join("tools", "visualisation", "graph.py"),
        os.path.join("frontend", "index.html"),
        os.path.join("frontend", "analytics.html"),
        os.path.join("frontend", "settings.html"),
        os.path.join("frontend", "prompt.html"),
        os.path.join("frontend", "export.html"),
        os.path.join("frontend", "error.html"),
        os.path.join("frontend", "css", "style.css"),
        os.path.join("frontend", "css", "theme.css"),
        os.path.join("frontend", "js", "api.js"),
        os.path.join("frontend", "js", "auth.js"),
        os.path.join("frontend", "js", "datalist.js"),
        os.path.join("frontend", "js", "settings.js"),
        os.path.join("frontend", "js", "analytics.js"),
        os.path.join("frontend", "js", "export.js"),
        os.path.join("frontend", "components", "auth-modals.html"),
        os.path.join("frontend", "components", "setup.html")
    ]

    try:
        print("\n[System Check] Verifying directory integrity...")
        
        # 1: auto-generate output directories seamlessly
        for directory in required_dirs:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                print(f"  -> Generated missing directory: {directory}/")

        # 2: auto-heal SQLite databases
        # auth database is corrupted or missing tables
        if os.path.exists("data/users.db") and not check_auth_setup():
            print("  -> Repairing anomalous Authentication database...")
            repair_auth_tables()

        # metrics database missing tables
        if not check_metrics_setup():
            print("  -> Repairing anomalous Metrics database...")
            repair_metrics_tables()
                
        # 2: detect missing source code
        missing_files : List[str] = [f for f in critical_files if not os.path.exists(f)]
        
        if not missing_files:
            return True
            
        print(f"\n[CRITICAL WARNING] Detected {len(missing_files)} missing system files.")
        for f in missing_files:
            print(f"  - {f}")
            
        # 3: auto-recovery prompt
        while True:
            user_choice : str = input("\nWould you like the system to attempt to download and restore these files from GitHub? (y/n): ").strip().lower()
            
            if user_choice == 'n':
                print("\n[HALTED] Auto-recovery aborted. Please manually pull the repository from GitHub using 'git pull'.")
                return False
                
            elif user_choice == 'y':
                print("\n[RECOVERY] Initiating GitHub download sequence...")
                failed_downloads : List[str] = []
                
                for file_path in missing_files:
                    success = _download_from_github(file_path)
                    if not success:
                        failed_downloads.append(file_path)
                        
                if failed_downloads:
                    print(f"\n[CRITICAL ERROR] Failed to restore {len(failed_downloads)} files after multiple attempts.")
                    print("Please check your internet connection or manually pull the repository via 'git pull'.")
                    return False
                    
                print("\n[SUCCESS] System integrity restored successfully!")
                return True
            else:
                print("Invalid input. Please enter 'y' or 'n'.")
                
    except KeyboardInterrupt:
        print("\n[HALTED] System check interrupted by user.")
        return False
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Failed to verify system integrity: {e}")
        return False