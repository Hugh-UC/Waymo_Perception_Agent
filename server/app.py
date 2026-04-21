"""
File: app.py
Title: FastAPI Backend Server
Description: Serves the frontend HTML/JS/CSS, handles local authentication, and provides REST API endpoints for configuration management.
Author: Hugh Brennan
Date: 2026-04-22
Version: 0.1
"""

import os
import yaml
import json
import hashlib
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Initialize the server with strict typing
app : FastAPI = FastAPI(title="Waymo Perception Agent API")

# Define absolute paths to prevent directory traversal issues
BASE_DIR : str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR : str = os.path.join(BASE_DIR, "frontend")
PARAMS_PATH : str = os.path.join(BASE_DIR, "config", "params.yaml")
ENV_PATH : str = os.path.join(BASE_DIR, ".env")
PREFS_JSON_PATH : str = os.path.join(BASE_DIR, "config", "settings.json")
AUTH_PATH : str = os.path.join(BASE_DIR, "config", "auth.json")

# ---------------------------------------------------------
# Pydantic Schemas for API Payloads
# ---------------------------------------------------------

class EnvSetup(BaseModel):
    """
    Pydantic schema for validating the incoming .env file setup request.
    """
    gemini_key : str
    news_key : str

class YamlUpdate(BaseModel):
    """
    Pydantic schema for validating the incoming params.yaml update request.
    """
    scraper : dict[str, Any]
    agent : dict[str, Any]

class UserPreferences(BaseModel):
    """
    Pydantic schema for validating the incoming JSON preferences backup request.
    """
    timestamp : int
    config : dict[str, Any]

class UserAccount(BaseModel):
    """
    Pydantic schema for secure user registration and login requests.
    """
    username : str
    password : str

# ---------------------------------------------------------
# Authentication & Setup Endpoints
# ---------------------------------------------------------

@app.get("/api/status")
async def get_system_status() -> dict[str, bool]:
    """
    Checks if the system requires first-time setup by verifying the existence 
    and population of the .env and auth.json files.

    Returns:
        dict[str, bool]: A dictionary containing a 'needs_setup' flag, which 
                         evaluates to True if either the .env keys are missing 
                         or the local admin account has not been created.
    """
    env_exists : bool = os.path.exists(ENV_PATH)
    auth_exists : bool = os.path.exists(AUTH_PATH)
    needs_env : bool = True
    
    if env_exists:
        with open(ENV_PATH, "r") as f:
            content : str = f.read()
            if "GEMINI_API_KEY" in content and "NEWS_API_KEY" in content:
                needs_env = False

    return {"needs_setup": needs_env or not auth_exists}

@app.post("/api/setup")
async def setup_env_file(keys : EnvSetup) -> dict[str, str]:
    """
    Creates or overwrites the local .env file with the provided API keys.

    Args:
        keys (EnvSetup): A structured payload containing the Gemini and News API keys.

    Raises:
        HTTPException: If the server encounters a file system error while writing the .env file.

    Returns:
        dict[str, str]: A status dictionary confirming successful generation.
    """
    try:
        with open(ENV_PATH, "w") as f:
            f.write(f'GEMINI_API_KEY="{keys.gemini_key}"\n')
            f.write(f'NEWS_API_KEY="{keys.news_key}"\n')
        return {"status": "success", "message": ".env generated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write .env: {str(e)}")

@app.post("/api/register")
async def register_user(user : UserAccount) -> dict[str, str]:
    """
    Hashes the provided password and saves the local admin account credentials to auth.json.

    Args:
        user (UserAccount): The plaintext username and password submitted during the setup wizard.

    Raises:
        HTTPException: If the server fails to create the config directory or write to auth.json.

    Returns:
        dict[str, str]: A status dictionary confirming successful registration.
    """
    hashed_pw : str = hashlib.sha256(user.password.encode()).hexdigest()
    try:
        os.makedirs(os.path.dirname(AUTH_PATH), exist_ok=True)
        with open(AUTH_PATH, "w") as f:
            json.dump({"username": user.username, "password": hashed_pw}, f)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/login")
async def login_api(user : UserAccount) -> dict[str, bool]:
    """
    Verifies incoming login credentials against the stored SHA-256 hash in auth.json.

    Args:
        user (UserAccount): The login attempt containing a username and plaintext password.

    Raises:
        HTTPException: If the auth.json file does not exist (status 404).

    Returns:
        dict[str, bool]: A dictionary containing an 'authenticated' boolean flag indicating success or failure.
    """
    if not os.path.exists(AUTH_PATH):
        raise HTTPException(status_code=404, detail="No account configured.")
        
    with open(AUTH_PATH, "r") as f:
        stored : dict[str, str] = json.load(f)
    
    attempt : str = hashlib.sha256(user.password.encode()).hexdigest()
    is_valid : bool = (user.username == stored["username"] and attempt == stored["password"])
    
    return {"authenticated": is_valid}

# ---------------------------------------------------------
# Configuration Endpoints
# ---------------------------------------------------------

@app.get("/api/config")
async def get_yaml_config() -> dict[str, Any]:
    """
    Reads the params.yaml file and sends it to the frontend settings page.

    Raises:
        HTTPException: If the server fails to read or parse the YAML file.

    Returns:
        dict[str, Any]: A dictionary representation of the core YAML configuration.
    """
    try:
        with open(PARAMS_PATH, "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read config: {str(e)}")

@app.post("/api/config")
async def update_yaml_config(new_config : YamlUpdate) -> dict[str, str]:
    """
    Overwrites the params.yaml file with the sanitized data sent from the frontend UI.

    Args:
        new_config (YamlUpdate): The structured payload containing the updated config parameters.

    Raises:
        HTTPException: If the server fails to write the YAML data to the file system.

    Returns:
        dict[str, str]: A status dictionary confirming successful update.
    """
    try:
        with open(PARAMS_PATH, "w") as f:
            yaml.dump(new_config.model_dump(), f, default_flow_style=False, sort_keys=False)
        return {"status": "success", "message": "params.yaml updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {str(e)}")

@app.get("/api/preferences")
async def get_user_preferences() -> dict[str, Any]:
    """
    Retrieves the backup settings.json file used for browser-to-file reconciliation.

    Raises:
        HTTPException: If the server fails to read or parse the JSON file.

    Returns:
        dict[str, Any]: A dictionary representation of user preferences, or a default 
                        empty configuration dictionary if the backup file does not exist.
    """
    if not os.path.exists(PREFS_JSON_PATH):
        return {"timestamp": 0, "config": {}}
    try:
        with open(PREFS_JSON_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read preferences: {str(e)}")

@app.post("/api/preferences")
async def save_user_preferences(prefs : UserPreferences) -> dict[str, str]:
    """
    Saves the user preferences to a persistent settings.json file with a unix timestamp.

    Args:
        prefs (UserPreferences): A structured payload containing the timestamp and config dictionary.

    Raises:
        HTTPException: If the server fails to write the JSON data to the file system.

    Returns:
        dict[str, str]: A status dictionary confirming successful backup.
    """
    try:
        os.makedirs(os.path.dirname(PREFS_JSON_PATH), exist_ok=True)
        with open(PREFS_JSON_PATH, "w") as f:
            json.dump(prefs.model_dump(), f, indent=4)
        return {"status": "success", "message": "settings.json updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save preferences: {str(e)}")

# ---------------------------------------------------------
# Static File Mounting & Routing
# ---------------------------------------------------------

@app.get("/")
async def serve_index() -> FileResponse:
    """
    Serves the root dashboard page.

    Returns:
        FileResponse: The index.html file located in the frontend directory.
    """
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/{page_name}.html")
async def serve_pages(page_name : str) -> FileResponse:
    """
    Dynamically routes and serves specific HTML pages from the frontend directory, 
    falling back to the custom 404 page if the file is missing.

    Args:
        page_name (str): The specific HTML file requested by the browser.

    Returns:
        FileResponse: The requested HTML file, or the 404.html fallback with a 404 status code.
    """
    file_path : str = os.path.join(FRONTEND_DIR, f"{page_name}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(FRONTEND_DIR, "404.html"), status_code=404)

@app.exception_handler(404)
async def custom_404_handler(request: Any, __: Any) -> FileResponse:
    """
    Intercepts standard FastAPI 404 errors and serves the custom HTML error page.

    Args:
        request (Any): The incoming request object that triggered the 404.
        __ (Any): The exception object (unused).

    Returns:
        FileResponse: The custom 404.html file with a 404 status code.
    """
    return FileResponse(os.path.join(FRONTEND_DIR, "404.html"), status_code=404)

# Mount the frontend directory to serve CSS and JS assets
app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")

if __name__ == "__main__":
    import uvicorn
    # Run the server on the local loopback address
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)