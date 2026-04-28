"""
File: app.py
Title: FastAPI Backend Server
Description: Serves the frontend HTML/JS/CSS, handles local authentication, and provides REST API endpoints for configuration management.
Author: Hugh Brennan
Date: 2026-04-22
Version: 0.1
"""
import os
import sys
import yaml
import json
import shutil
import re
from typing import Any
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel

# initialize server with strict typing
app : FastAPI = FastAPI(title="Waymo Perception Agent API")

# define absolute paths, prevent directory traversal issues
BASE_DIR : str              = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
FRONTEND_DIR : str          = os.path.join(BASE_DIR, "frontend")
ENV_PATH : str              = os.path.join(BASE_DIR, ".env")
PARAMS_PATH : str           = os.path.join(BASE_DIR, "config", "params.yaml")
PREFS_JSON_PATH : str       = os.path.join(BASE_DIR, "config", "settings.json")
MODELS_DEFAULT_PATH : str   = os.path.join(BASE_DIR, "config", "models.base.json")
MODELS_PATH : str           = os.path.join(BASE_DIR, "config", "models.json")
USER_DB_PATH : str          = os.path.join(BASE_DIR, "data", "users.db")

# Package Imports
from tools.db import get_dashboard_totals, get_narratives, check_metrics_setup
from tools.auth_db import create_user, verify_user, check_auth_setup, get_all_users, delete_user
from main import run_pipeline

# ---------------------------------------------------------
# Pydantic Schemas for API Payloads
# ---------------------------------------------------------
class EnvSetup(BaseModel):
    """
    Pydantic schema for validating the incoming .env file setup request.
    """
    gemini_key : str
    news_key : str
    youtube_key : str | None = None
    gcs_key : str | None = None
    gcs_cx : str | None = None

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
    email : str = "admin@local.host" # default fallback for initial setup wizard

class NewUser(BaseModel):
    """
    Schema for adding new users via the Admin dashboard.
    """
    username: str
    email: str
    password: str
    role: str
    job_title: str = ""


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
    env_exists : bool       = os.path.exists(ENV_PATH)
    auth_exists : bool      = check_auth_setup()
    metrics_exists : bool   = check_metrics_setup()
    
    # component flags
    missing_env : bool      = not env_exists
    missing_auth : bool     = not auth_exists
    missing_metrics : bool  = not metrics_exists
    missing_config : bool   = not os.path.exists(PARAMS_PATH)
    
    # 1. map .env api key states and create masked versions
    api_key_mapping : list[str] = {
        'GEMINI_API_KEY': 'masked_gemini',
        'NEWS_API_KEY': 'masked_news',
        'YOUTUBE_API_KEY': 'masked_yt',
        'GCS_API_KEY': 'masked_gcs',
        'GCS_CX_ID': 'masked_cx'
    }

    # initialize all masked variables to None
    masked_data : dict[str, str | None] = {v: None for v in api_key_mapping.values()}

    # extract and mask
    if env_exists:
        with open(ENV_PATH, "r") as f:
            content : str = f.read()

            for env_key, mask_key in api_key_mapping.items():
                # match regex for keys
                match : re.Match[str] = re.search(fr'{env_key}=["\']?(.*?)["\']?(?:\n|$)', content)

                if match and match.group(1).strip():
                    val : str = match.group(1).strip()
                    masked_data[mask_key] = "*" * 12 + val[-4:] if len(val) > 4 else "***"

            # check for required keys, flag environment as missing
            missing_env : bool = not (masked_data['masked_gemini'] and masked_data['masked_news'])

    # 2. parse params.yaml
    config_data : dict[str, Any] | None = None
    if not missing_config:
        try:
            with open(PARAMS_PATH, "r") as f:
                config_data = yaml.safe_load(f)
                if config_data and "agent" in config_data:
                    missing_config = False
        except Exception:
            missing_config = True

    # 3. determine overall setup state
    needs_setup : bool = missing_env or missing_config or missing_auth

    return {
        "needs_setup": needs_setup,
        "missing_env": missing_env,
        "missing_config": missing_config,
        "missing_auth": missing_auth,
        "missing_metrics": missing_metrics,
        **masked_data,
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
        # map pydantic schema fields to exact .env key
        payload_map = {
            'gemini_key': 'GEMINI_API_KEY',
            'news_key': 'NEWS_API_KEY',
            'youtube_key': 'YOUTUBE_API_KEY',
            'gcs_key': 'GCS_API_KEY',
            'gcs_cx': 'GCS_CX_ID'
        }

        # initialize existing keys dict
        existing_keys = {env_key: "" for env_key in payload_map.values()}

        # read existing keys, prevent overwriting with blanks/masks
        if os.path.exists(ENV_PATH):
            with open(ENV_PATH, "r") as f:
                content = f.read()

                for env_key in payload_map.values():
                    match = re.search(fr'{env_key}=["\']?(.*?)["\']?(?:\n|$)', content)
                    if match:
                        existing_keys[env_key] = match.group(1).strip()

        # write keys into .env
        with open(ENV_PATH, "w") as f:
            for py_key, env_key in payload_map.items():
                # extract incoming value from pydantic 'keys' object
                new_val = getattr(keys, py_key)
                
                # use new valid value, otherwise keep old value
                final_val = new_val if (new_val and "*" not in new_val) else existing_keys[env_key]
                f.write(f'{env_key}="{final_val}"\n')

        return {"status": "success", "message": ".env generated."}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write .env: {str(e)}")

@app.post("/api/register")
async def register_user(user : UserAccount) -> dict[str, str]:
    """
    Saves the initial local admin account credentials to the SQLite database.

    Args:
        user (UserAccount): plaintext username and password submitted during the setup wizard.

    Raises:
        HTTPException: if the server fails to create the config directory or write to auth.json.

    Returns:
        dict[str, str]: status dictionary confirming successful registration.
    """
    try:
        # force first user to be a Global Admin
        success : bool = create_user(
            username=user.username, 
            email=user.email, 
            password=user.password, 
            role="admin", 
            job_title="Global Administrator"
        )
        if success:
            return {"status": "success"}
        else:
            raise HTTPException(status_code=400, detail="Username or Email already exists.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/login")
async def login_api(user : UserAccount) -> dict[str, bool]:
    """
    Verifies incoming login credentials against the stored SHA-256 hash in auth.json.

    Args:
        user (UserAccount): login attempt containing a username and plaintext password.

    Returns:
        dict[str, bool]: dictionary containing an 'authenticated' boolean flag indicating success or failure.
    """
    if not os.path.exists(USER_DB_PATH):
        raise HTTPException(status_code=404, detail="System not initialized.")
        
    user_data = verify_user(user.username, user.password)
    
    if user_data:
        # Rrturn role so frontend knows what UI elements to unlock
        return {"authenticated": True, "role": user_data["role"]}
    
    return {"authenticated": False}

@app.post("/api/reset")
async def factory_reset_system() -> dict[str, str]:
    """
    Performs a catastrophic factory reset. Deletes API keys, auth credentials, 
    and the SQLite database. Overwrites params.yaml with baseline defaults.

    Raises:
        HTTPException: if server encounters file system error while attempting 
                       to delete files or rewrite configuration (status 500).

    Returns:
        dict[str, str]: status dictionary confirming successful wipe and system reset.
    """
    try:
        # 1. delete auth & environment
        if os.path.exists(USER_DB_PATH): os.remove(USER_DB_PATH) # Delete User DB
        if os.path.exists(ENV_PATH): os.remove(ENV_PATH)
        
        # 2. delete database
        db_path : str = os.path.join(BASE_DIR, "data", "waymo_metrics.db")
        if os.path.exists(db_path): os.remove(db_path)

        # 3. reset available models data
        if os.path.exists(MODELS_PATH): 
            os.remove(MODELS_PATH)

        if os.path.exists(MODELS_DEFAULT_PATH):
            shutil.copy(MODELS_DEFAULT_PATH, MODELS_PATH)
        
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
# User Management Endpoints
# ---------------------------------------------------------
@app.get("/api/roles")
async def get_roles() -> dict[str, Any]:
    """
    Retrieves the roles.json file to populate frontend dropdowns.

    Returns:
        dict[str, Any]: dictionary representation of the roles and their associated permission scopes.
    """
    roles_path = os.path.join(BASE_DIR, "config", "roles.json")
    if not os.path.exists(roles_path):
        return {"roles": {}}
    with open(roles_path, "r") as f:
        return json.load(f)

@app.get("/api/users")
async def fetch_users() -> list[dict[str, Any]]:
    """
    Retrieves all registered users.

    Returns:
        list[dict[str, Any]]: list of dictionaries, where each dictionary represents a user's profile data (excluding password hashes).
    """
    return get_all_users()

@app.post("/api/users/add")
async def add_new_user(user: NewUser) -> dict[str, str]:
    """
    Creates a new user from the admin dashboard.

    Args:
        user (NewUser): structured payload containing the new user's credentials and role assignments.

    Raises:
        HTTPException: if provided username or email already exists in database (status 400).

    Returns:
        dict[str, str]: status dictionary confirming successful creation.
    """
    success = create_user(user.username, user.email, user.password, user.role, user.job_title)
    if success:
        return {"status": "success", "message": "User added successfully."}
    raise HTTPException(status_code=400, detail="Username or email already exists.")

@app.delete("/api/users/{user_id}")
async def remove_user(user_id: int) -> dict[str, str]:
    """
    Deletes a user. Prevents deletion of the Master Admin (ID 1).

    Args:
        user_id (int): unique integer ID of the user to be deleted.

    Raises:
        HTTPException: If an attempt is made to delete Master Administrator (ID 1) (status 403).
        HTTPException: If database deletion operation fails (status 500).

    Returns:
        dict[str, str]: status dictionary confirming successful deletion.
    """
    if user_id == 1:
        raise HTTPException(status_code=403, detail="Cannot delete the Master Administrator.")
    
    if delete_user(user_id):
        return {"status": "success"}
    raise HTTPException(status_code=500, detail="Failed to delete user.")


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
    
@app.get("/api/models")
async def get_available_models() -> dict[str, list[str]]:
    """
    Auto-generates the local models.json from the default template if missing.
    Parses the provider library and returns a flat list of all locked and 
    custom models for the frontend dropdowns.

    Returns:
        dict[str, list[str]]: dictionary containing a single 'models' key mapped to a flattened list of available model strings.
    """
    # bullet proof fallback models dictionary
    fallback : dict[str, list[str]] = {"models": ["gemini-3.1-pro-preview", "gemini-3-flash-preview", "gemini-2.5-pro", "gemini-2.5-flash"]}

    # auto-copy template (base) if local instance doesn't exist
    if not os.path.exists(MODELS_PATH) and os.path.exists(MODELS_DEFAULT_PATH):
        shutil.copy(MODELS_DEFAULT_PATH, MODELS_PATH)

    # use fallback incase file is not created
    if not os.path.exists(MODELS_PATH):
        return fallback
        
    try:
        with open(MODELS_PATH, "r") as f:
            data : dict[str, Any] = json.load(f)
            
        all_models : list[str] = []
        providers : dict[str, Any] = data.get("providers", {})
        
        # flatten locked and custom arrays
        for provider_data in providers.values():
            all_models.extend(provider_data.get("locked_defaults", []))
            all_models.extend(provider_data.get("custom_added", []))
            
        return {"models": all_models}
    except Exception as e:
        return fallback


# ---------------------------------------------------------
# Execution Endpoints
# ---------------------------------------------------------
@app.post("/api/run-scraper")
async def trigger_scraper() -> dict[str, str]:
    """
    Executes the full AI scraping, analysis, and database export pipeline.

    Raises:
        HTTPException: if the pipeline encounters a critical failure during execution.

    Returns:
        dict[str, str]: A success status message upon completion.
    """
    try:
        success : bool = await run_pipeline()
        if success:
            return {"status": "success", "message": "Scraping, AI analysis, and exports complete."}
        else:
            raise HTTPException(status_code=500, detail="Pipeline failed during execution. Check terminal logs.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/analytics/narratives")
async def fetch_narratives(start : str | None = None, end : str | None = None) -> dict[str, list[dict[str, Any]]]:
    """
    Retrieves AI-synthesized narratives from the database layer, dynamically filtered by chronological parameters.

    Args:
        start (str | None, optional): start date string (YYYY-MM-DD). Defaults to None.
        end (str | None, optional): end date string (YYYY-MM-DD). Defaults to None.

    Returns:
        dict[str, list[dict[str, Any]]]: dictionary containing a list of narrative records.
    """
    narratives = get_narratives(start=start, end=end)
    return {"narratives": narratives}

@app.get("/api/dashboard/summary")
async def get_dashboard_summary() -> dict[str, int]:
    """
    Fetches the all-time totals for the dashboard from the database layer.

    Returns:
        dict[str, int]: dictionary containing 'total_runs' and 'total_sources'.
    """
    return get_dashboard_totals()


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
    
    # prevent users from bypassing Python HTML injector
    if page_name == "index":
        return RedirectResponse(url="/", status_code=302)

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



# mount frontend directory to serve CSS and JS assets
app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend")


if __name__ == "__main__":
    import uvicorn
    # run server (local loopback address)
    uvicorn.run("server.app:app", host="127.0.0.1", port=8000, reload=True)