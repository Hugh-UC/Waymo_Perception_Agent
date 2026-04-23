/**
 * File: api.js
 * Title: API Communication & Global Security Gatekeeper
 * Description: Centralises all fetch requests to the FastAPI backend and enforces 
 * strict routing rules based on the system's setup and session state.
 * Author: Hugh Brennan
 * Date: 2026-04-22
 * Version: 0.4
 */

const API = {
    // ---------------------------------------------------------
    // Boot & Authentication Endpoints
    // ---------------------------------------------------------
    
    /**
     * Fetches the system status to determine if initial setup is required.
     * Expected Response: { needs_setup, missing_env, missing_config, missing_auth, masked_gemini, masked_news, config }
     */
    async getStatus() {
        const res = await fetch("/api/status");
        if (!res.ok) throw await res.json();
        return res.json();
    },

    /**
     * Fetches high-level database metrics for the main dashboard.
     * Expected Response: { total_runs, total_sources }
     */
    async getDashboardSummary() {
        const res = await fetch("/api/dashboard/summary");
        if (!res.ok) throw await res.json();
        return res.json();
    },

    /**
     * Submits the Gemini and News API keys to generate the .env file.
     * @param {Object} payload - Object containing gemini_key and/or news_key.
     */
    async setupKeys(payload) {
        const res = await fetch("/api/setup", {
            method: "POST", 
            headers: { "Content-Type": "application/json" }, 
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw await res.json();
        return res.json();
    },

    /**
     * Registers the local administrator account.
     * @param {Object} payload - { username: string, password: string }
     */
    async registerUser(payload) {
        const res = await fetch("/api/register", {
            method: "POST", 
            headers: { "Content-Type": "application/json" }, 
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw await res.json();
        return res.json();
    },

    /**
     * Authenticates an existing administrator.
     * @param {Object} payload - { username: string, password: string }
     */
    async loginUser(payload) {
        const res = await fetch("/api/login", {
            method: "POST", 
            headers: { "Content-Type": "application/json" }, 
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw await res.json();
        return res.json();
    },

    // ---------------------------------------------------------
    // Configuration Endpoints (For settings.js & setup models)
    // ---------------------------------------------------------
    
    async getConfig() {
        const res = await fetch("/api/config");
        if (!res.ok) throw await res.json();
        return res.json();
    },
    
    async updateConfig(payload) {
        const res = await fetch("/api/config", {
            method: "POST", 
            headers: { "Content-Type": "application/json" }, 
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw await res.json();
        return res.json();
    },
    
    async getPreferences() {
        const res = await fetch("/api/preferences");
        if (!res.ok) throw await res.json();
        return res.json();
    },
    
    async savePreferences(payload) {
        const res = await fetch("/api/preferences", {
            method: "POST", 
            headers: { "Content-Type": "application/json" }, 
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw await res.json();
        return res.json();
    }
};

const BootManager = {
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
                
                // unlock the wizard overlay and prepopulate forms
                document.getElementById("setup-wizard").classList.remove("hidden");
                if (window.AuthManager) {
                    window.AuthManager.initializeWizardState(status);
                }
                
            } else {
                // RULE 2: setup is 100% complete, check for active session cookie
                if (!window.AuthManager || !window.AuthManager.getSession()) {
                    
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

// expose SDK tools to the global window object
window.API = API;
window.BootManager = BootManager;