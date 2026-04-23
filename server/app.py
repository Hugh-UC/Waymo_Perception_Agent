"""
File: app.py
Title: FastAPI Backend Server
Description: Serves the frontend HTML/JS/CSS, handles local authentication, and provides REST API endpoints for configuration management.
Author: Hugh Brennan
Date: 2026-04-22
Version: 0.2
"""
import os
import yaml
import json
import hashlib
import re
import sqlite3
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel

# initialize server with strict typing
app : FastAPI = FastAPI(title="Waymo Perception Agent API")

# define absolute paths, prevent directory traversal issues
BASE_DIR : str          = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR : str      = os.path.join(BASE_DIR, "frontend")
PARAMS_PATH : str       = os.path.join(BASE_DIR, "config", "params.yaml")
ENV_PATH : str          = os.path.join(BASE_DIR, ".env")
PREFS_JSON_PATH : str   = os.path.join(BASE_DIR, "config", "settings.json")
AUTH_PATH : str         = os.path.join(BASE_DIR, "config", "auth.json")


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
async def get_system_status() -> dict[str, Any]:
    """
    Checks the granular status of the system to drive the frontend Setup Wizard routing.
    Parses the .env file to dynamically generate masked API keys.

    Returns:
        dict[str, Any]: highly detailed dictionary containing boolean flags for missing 
                        components, masked string values, and the current YAML config.
    """
    env_exists : bool  = os.path.exists(ENV_PATH)
    auth_exists : bool = os.path.exists(AUTH_PATH)
    
    # component flags
    missing_env : bool    = True
    missing_auth : bool   = not auth_exists
    missing_config : bool = True
    
    # extracted data
    masked_gemini : str | None = None
    masked_news : str | None = None
    config_data : dict[str, Any] | None = None
    
    # 1. parse .env and mask keys
    if env_exists:
        with open(ENV_PATH, "r") as f:
            content : str = f.read()
            
            # regex search for keys
            g_match = re.search(r'GEMINI_API_KEY=["\']?(.*?)["\']?(?:\n|$)', content)
            n_match = re.search(r'NEWS_API_KEY=["\']?(.*?)["\']?(?:\n|$)', content)
            
            if g_match and n_match:
                g_key : str = g_match.group(1).strip()
                n_key : str = n_match.group(1).strip()
                
                if g_key and n_key:
                    missing_env = False
                    masked_gemini = "*" * 12 + g_key[-4:] if len(g_key) > 4 else "***"
                    masked_news = "*" * 12 + n_key[-4:] if len(n_key) > 4 else "***"

    # 2. parse params.yaml
    if os.path.exists(PARAMS_PATH):
        try:
            with open(PARAMS_PATH, "r") as f:
                config_data = yaml.safe_load(f)
                if config_data and "agent" in config_data:
                    missing_config = False
        except Exception:
            pass

    # 3. determine overall setup state
    needs_setup : bool = missing_env or missing_config or missing_auth

    return {
        "needs_setup": needs_setup,
        "missing_env": missing_env,
        "missing_config": missing_config,
        "missing_auth": missing_auth,
        "masked_gemini": masked_gemini,
        "masked_news": masked_news,
        "config": config_data
    }

@app.post("/api/setup")
async def setup_env_file(keys : EnvSetup) -> dict[str, str]:
    """
    Creates or overwrites the local .env file with the provided API keys.
    If the frontend sends an empty string (or the masked string), it skips writing 
    that specific key to prevent overwriting valid keys with asterisks.

    Args:
        keys (EnvSetup): structured payload containing the Gemini and News API keys.

    Raises:
        HTTPException: if the server encounters a file system error while writing the .env file.

    Returns:
        dict[str, str]: status dictionary confirming successful generation.
    """
    try:
        # read existing keys, prevent overwriting with blanks/masks
        existing_g_key = ""
        existing_n_key = ""
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH, "r") as f:
                content = f.read()
                g_match = re.search(r'GEMINI_API_KEY=["\']?(.*?)["\']?(?:\n|$)', content)
                n_match = re.search(r'NEWS_API_KEY=["\']?(.*?)["\']?(?:\n|$)', content)
                if g_match: existing_g_key = g_match.group(1)
                if n_match: existing_n_key = n_match.group(1)

        # update if frontend provided a real, unmasked string
        final_g_key = keys.gemini_key if (keys.gemini_key and "*" not in keys.gemini_key) else existing_g_key
        final_n_key = keys.news_key if (keys.news_key and "*" not in keys.news_key) else existing_n_key

        # write keys into .env
        with open(ENV_PATH, "w") as f:
            f.write(f'GEMINI_API_KEY="{final_g_key}"\n')
            f.write(f'NEWS_API_KEY="{final_n_key}"\n')
        return {"status": "success", "message": ".env generated."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write .env: {str(e)}")

@app.post("/api/register")
async def register_user(user : UserAccount) -> dict[str, str]:
    """
    Hashes the provided password and saves the local admin account credentials to auth.json.

    Args:
        user (UserAccount): plaintext username and password submitted during the setup wizard.

    Raises:
        HTTPException: if the server fails to create the config directory or write to auth.json.

    Returns:
        dict[str, str]: status dictionary confirming successful registration.
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
        user (UserAccount): login attempt containing a username and plaintext password.

    Raises:
        HTTPException: if the auth.json file does not exist (status 404).

    Returns:
        dict[str, bool]: dictionary containing an 'authenticated' boolean flag indicating success or failure.
    """
    if not os.path.exists(AUTH_PATH):
        raise HTTPException(status_code=404, detail="No account configured.")
        
    with open(AUTH_PATH, "r") as f:
        stored : dict[str, str] = json.load(f)
    
    attempt : str = hashlib.sha256(user.password.encode()).hexdigest()
    is_valid : bool = (user.username == stored["username"] and attempt == stored["password"])
    
    return {"authenticated": is_valid}

@app.post("/api/reset")
async def factory_reset_system() -> dict[str, str]:
    """
    Performs a catastrophic factory reset. Deletes API keys, auth credentials, 
    and the SQLite database. Overwrites params.yaml with baseline defaults.

    Raises:
        HTTPException: _description_

    Returns:
        dict[str, str]: _description_
    """
    try:
        # 1. delete auth & environment
        if os.path.exists(AUTH_PATH): os.remove(AUTH_PATH)
        if os.path.exists(ENV_PATH): os.remove(ENV_PATH)
        
        # 2. delete database
        db_path : str = os.path.join(BASE_DIR, "data", "waymo_metrics.db")
        if os.path.exists(db_path): os.remove(db_path)
        
        # 3. restore params.yaml to safe defaults
        default_config = {
            "scraper": {
                "news": {"query": "Waymo", "days_back": 3, "max_articles": 15},
                "reddit": {"subreddit": ["SelfDrivingCars", "Waymo", "AutonomousVehicles"], "max_posts": 8}
            }, 
            "agent": {
                "model_name": "gemini-2.5-flash",
                "fallback_model": ["gemini-3-flash-preview"],
                "temperature": 0.2,
                "retries": 3,
                "output_retries": 5
            }
        }
        with open(PARAMS_PATH, "w") as f:
            yaml.dump(default_config, f, default_flow_style=False, sort_keys=False)

        return {"status": "success", "message": "System factory reset complete."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")


# ---------------------------------------------------------
# Configuration Endpoints
# ---------------------------------------------------------
@app.get("/api/config")
async def get_yaml_config() -> dict[str, Any]:
    """
    Reads the params.yaml file and sends it to the frontend settings page.

    Raises:
        HTTPException: if the server fails to read or parse the YAML file.

    Returns:
        dict[str, Any]: dictionary representation of the core YAML configuration.
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
        new_config (YamlUpdate): structured payload containing the updated config parameters.

    Raises:
        HTTPException: if the server fails to write the YAML data to the file system.

    Returns:
        dict[str, str]: status dictionary confirming successful update.
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
        HTTPException: if the server fails to read or parse the JSON file.

    Returns:
        dict[str, Any]: dictionary representation of user preferences, or a default 
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
        prefs (UserPreferences): structured payload containing the timestamp and config dictionary.

    Raises:
        HTTPException: if the server fails to write the JSON data to the file system.

    Returns:
        dict[str, str]: status dictionary confirming successful backup.
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
async def serve_index() -> HTMLResponse:
    """
    Serves the root dashboard page.
    Dynamically reads and injects the setup wizard and reset modal HTML using 
    native string replacement (zero-dependency).

    Returns:
        HTMLResponse: dynamically assembled index HTML content.
    """
    # 1. check system status internally
    status_data = await get_system_status()
    
    # 2. read base index.html file
    index_path : str = os.path.join(FRONTEND_DIR, "index.html")
    with open(index_path, "r", encoding="utf-8") as f:
        html_content : str = f.read()

    # 3. inject or remove the setup HTML based on status
    if status_data["needs_setup"]:
        setup_path : str = os.path.join(FRONTEND_DIR, "components", "setup.html")
        with open(setup_path, "r", encoding="utf-8") as f:
            setup_content : str = f.read()
        
        # append setup code into the placeholder
        html_content = html_content.replace('<div id="setup-placeholder"></div>', setup_content)
    else:
        # delete the placeholder to keep DOM clean
        html_content = html_content.replace('<div id="setup-placeholder"></div>', "")

    # 4. unconditionally inject the login modal
    auth_modals_path : str = os.path.join(FRONTEND_DIR, "components", "auth-modals.html")
    if os.path.exists(auth_modals_path):
        with open(auth_modals_path, "r", encoding="utf-8") as f:
            reset_content : str = f.read()
        html_content = html_content.replace('<div id="auth-placeholder"></div>', reset_content)

    # 4. send assembled page to browser
    return HTMLResponse(content=html_content)

@app.get("/{page_name}.html", response_model=None)
async def serve_pages(page_name : str) -> FileResponse | RedirectResponse:
    """
    Dynamically routes and serves specific HTML pages from the frontend directory.
    If the file is missing, redirects to the dynamic error page.

    Args:
        page_name (str): specific HTML file requested by the browser.

    Returns:
        RedirectResponse: requested HTML file, or a redirect to the dynamic error page.
    """
    if page_name == "error":
        return FileResponse(os.path.join(FRONTEND_DIR, "error.html"))
    
    file_path : str = os.path.join(FRONTEND_DIR, f"{page_name}.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    
    return RedirectResponse(url="/error.html?code=404", status_code=302)

@app.exception_handler(404)
async def custom_404_handler(request: Any, __: Any) -> RedirectResponse:
    """
    Intercepts standard FastAPI 404 errors and redirects to the custom dynamic error page.

    Args:
        request (Any): incoming request object that triggered the 404.
        __ (Any): exception object (unused).

    Returns:
        RedirectResponse: 302 redirect to the dynamic error page with a 404 code parameter.
    """
    return RedirectResponse(url="/error.html?code=404", status_code=302)

@app.exception_handler(500)
async def custom_500_handler(request: Any, exc: Exception) -> RedirectResponse:
    """
    Intercepts catastrophic server crashes and redirects to the dynamic error page,
    passing the python exception string to the frontend.

    Args:
        request (Any): incoming request object.
        exc (Exception): unhandled exception that caused the 500 error.

    Returns:
        RedirectResponse: 302 redirect to the dynamic error page with a 500 code and error details.
    """
    error_detail = str(exc).replace("\n", " ")
    return RedirectResponse(url=f"/error.html?code=500&detail={error_detail}", status_code=302)


@app.get("/api/dashboard/summary")
async def get_dashboard_summary() -> dict[str, int]:
    """
    Queries the SQLite database to fetch the all-time totals for the dashboard.

    Raises:
        HTTPException: if there is an error connecting to or reading from the database.

    Returns:
        dict[str, int]: dictionary containing 'total_runs' and 'total_sources'.
    """
    db_path : str = os.path.join(BASE_DIR, "data", "waymo_metrics.db")
    
    # return zeros, if daatabase doesnt exists
    if not os.path.exists(db_path):
        return {"total_runs": 0, "total_sources": 0}
        
    try:
        # create connection to database
        conn : sqlite3.Connection   = sqlite3.connect(db_path)
        cursor : sqlite3.Cursor     = conn.cursor()
        
        # sum counts from daily overview table
        cursor.execute("SELECT SUM(run_count), SUM(source_total) FROM daily_overview")
        row = cursor.fetchone()
        conn.close()
        
        return {
            "total_runs": row[0] if row[0] else 0,
            "total_sources": row[1] if row[1] else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database read error: {str(e)}")

# mount frontend directory to serve CSS and JS assets
app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")


if __name__ == "__main__":
    import uvicorn
    # run server (local loopback address)
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)