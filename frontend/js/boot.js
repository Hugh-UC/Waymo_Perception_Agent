/**
 * File: boot.js
 * Title: Global Boot Controller & Security Gatekeeper
 * Description: Acts as the primary entry point for the application. Checks server 
 * status and session validity before routing to the Setup Wizard, Login, or App.
 * Author: Hugh Brennan
 * Date: 2026-05-05
 * Version: 0.1
 */

// import dependencies
import { API } from './api.js';
import { AuthManager, AuthUIController } from './auth.js';

class BootManager {
    /**
     * Acts as the Global Route Gatekeeper. Pings the backend on page load.
     * Enforces redirects if the user attempts to bypass setup or login.
     */
    static async initialize() {
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
                        await this.loadDashboardMetrics();
                    }
                }
            }
        } catch (error) {
            console.error("[Boot Error] System initialization failed:", error);
        }
    }

    static async loadDashboardMetrics() {
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

// ---------------------------------------------------------
// Master Application Initialization
// ---------------------------------------------------------
document.addEventListener("DOMContentLoaded", async () => {
    // run security gatekeeper & setup routing
    await BootManager.initialize();
    
    // attach global auth & setup ui events
    await AuthUIController.init();
});