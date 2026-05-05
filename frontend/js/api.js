/**
 * File: api.js
 * Title: API Communication & Global Security Gatekeeper
 * Description: Centralises all fetch requests to the FastAPI backend and enforces 
 * strict routing rules based on the system's setup and session state. (SDK Tools)
 * Author: Hugh Brennan
 * Date: 2026-04-22
 * Version: 0.1
 */
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