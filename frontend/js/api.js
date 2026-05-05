/**
 * File: api.js
 * Title: API Communication & Global Security Gatekeeper
 * Description: Centralises all fetch requests to the FastAPI backend and enforces 
 * strict routing rules based on the system's setup and session state. (SDK Tools)
 * Author: Hugh Brennan
 * Date: 2026-04-22
 * Version: 0.1
 */

// import authentication manager to handle session checks during boot
import { AuthManager } from './auth.js';


export const API = {
    /**
     * Master internal request router. Handles headers, body serialization, and error throwing.
     * 
     * @param {string} endpoint - The API route to call.
     * @param {string} [method="GET"] - The HTTP method to use (e.g., "GET", "POST", "DELETE").
     * @param {Object|null} [payload=null] - Optional JSON body to send with the request.
     * @returns {Promise<Object>} The parsed JSON response from the server.
     * @throws {Object} Throws the parsed JSON error response if the request fails.
     */
    async _request(endpoint, method = "GET", payload = null) {
        const options = { method, headers: {} };
        
        if (payload) {
            options.headers["Content-Type"] = "application/json";
            options.body = JSON.stringify(payload);
        }

        const res = await fetch(endpoint, options);
        if (!res.ok) throw await res.json();
        return res.json();
    },

    // ---------------------------------------------------------
    // Boot & Authentication Endpoints
    // ---------------------------------------------------------
    /**
     * Fetches the system status to determine if initial setup is required.
     * Expected Response: { needs_setup, missing_env, missing_config, missing_auth, masked_gemini, masked_news, config }
     */
    getStatus: () => API._request("/api/status"),

    /**
     * Fetches high-level database metrics for the main dashboard.
     * Expected Response: { total_runs, total_sources }
     */
    getDashboardSummary: () => API._request("/api/dashboard/summary"),

    /**
     * Submits the Gemini and News API keys to generate the .env file.
     * @param {Object} payload - Object containing gemini_key and/or news_key.
     */
    setupKeys: (payload) => API._request("/api/setup", "POST", payload),

    /**
     * Triggers the backend AI pipeline execution.
     * Expected Response: { status, message }
     */
    runScraper: () => API._request("/api/run-scraper", "POST"),

    /**
     * Registers the local administrator account.
     * @param {Object} payload - { username: string, password: string, email: string, role: string, job_title: string }
     */
    registerUser: (payload) => API._request("/api/register", "POST", payload),

    /**
     * Authenticates an existing administrator.
     * @param {Object} payload - { username: string, password: string }
     */
    loginUser: (payload) => API._request("/api/login", "POST", payload),

    /**
     * Triggers a catastrophic system wipe (deletes auth, keys, and DB).
     */
    factoryReset: () => API._request("/api/reset", "POST"),

    // ---------------------------------------------------------
    // Configuration Endpoints (For settings.js & setup models)
    // ---------------------------------------------------------
    /**
     * Retrieves the current system configuration from params.yaml.
     * @returns {Promise<Object>} The parsed YAML configuration.
     */
    getConfig: () => API._request("/api/config"),

    /**
     * Overwrites the params.yaml file with updated configuration data.
     * @param {Object} payload - The new configuration structure to save.
     */
    updateConfig: (payload) => API._request("/api/config", "POST", payload),

    /**
     * Retrieves the user's browser-backed preferences (settings.json).
     * @returns {Promise<Object>} The latest saved preferences and timestamp.
     */
    getPreferences: () => API._request("/api/preferences"),

    /**
     * Saves the current UI state to the backend as a JSON backup.
     * @param {Object} payload - { timestamp: number, config: Object }
     */
    savePreferences: (payload) => API._request("/api/preferences", "POST", payload),

    // ---------------------------------------------------------
    // User Management Endpoints
    // ---------------------------------------------------------
    /**
     * Retrieves the predefined list of user roles and permissions.
     * @returns {Promise<Object>} Dictionary of available roles.
     */
    getRoles: () => API._request("/api/roles"),
    
    /**
     * Fetches all registered users from the database.
     * @returns {Promise<Array>} List of user objects (excluding password hashes).
     */
    getUsers: () => API._request("/api/users"),
    
    /**
     * Adds a new user from the admin dashboard.
     * @param {Object} payload - { username, email, password, role, job_title }
     */
    addUser: (payload) => API._request("/api/users/add", "POST", payload),
    
    /**
     * Deletes a specific user from the database.
     * @param {number} userId - The unique ID of the user to remove.
     */
    deleteUser: (userId) => API._request(`/api/users/${userId}`, "DELETE"),

    /**
     * Fetches the registered AI models to populate the custom dropdowns.
     * @returns {Promise<Object>} Object containing an array of available models.
     */
    getModels: () => API._request("/api/models")
};

export const BootManager = {
    /**
     * Acts as the Global Route Gatekeeper. Pings the backend on page load.
     * Enforces redirects if the user attempts to bypass setup or login.
     */
    async initialize() {
        const currentPath = window.location.pathname;
        const isIndex = currentPath === '/' || currentPath.endsWith('index.html');
        
        try {
            const status = await API.getStatus();

            if (status.needs_setup) {
                // RULE 1: if any setup is missing, force the user to index.html
                if (!isIndex) { 
                    window.location.href = '/'; 
                    return; 
                }
                
                // RULE 2: check if the wizard exists before unlocking
                const wizard = document.getElementById("setup-wizard");
                if (wizard) {
                    wizard.classList.remove("hidden");
                } else {
                    console.error("Critical: setup-wizard not found in DOM. Python injection bypassed.");
                }
                
                // unlock the wizard overlay and prepopulate forms
                document.getElementById("setup-wizard").classList.remove("hidden");
                if (AuthManager) {
                    AuthManager.initializeWizardState(status);
                }
                
            } else {
                // RULE 2: setup is 100% complete, check for active session cookie
                if (!AuthManager || !AuthManager.getSession()) {
                    
                    // no session exists, force user to index.html
                    if (!isIndex) { 
                        window.location.href = '/'; 
                        return; 
                    }
                    
                    document.getElementById("login-overlay").classList.remove("hidden");
                } else {
                    // RULE 3: valid session confirmed, unlock application container
                    const app = document.getElementById("app-container");
                    if (app) {
                        app.classList.remove("hidden");
                    }
                    
                    const logoutBtn = document.getElementById("btn-logout");
                    if (logoutBtn) {
                        logoutBtn.classList.remove("hidden");
                    }

                    // populate dashboard metrics
                    if (isIndex) {
                        try {
                            const metrics = await API.getDashboardSummary();
                            const statValues = document.querySelectorAll(".stat-value");
                            if (statValues.length >= 2) {
                                statValues[0].textContent = metrics.total_runs;
                                statValues[1].textContent = metrics.total_sources;
                            }
                        } catch (error) {
                            console.error("Failed to load dashboard metrics:", error);
                        }
                    }
                }
            }
        } catch (error) {
            console.error("[Boot Error] System initialization failed:", error);
        }
    }
};