/**
 * File: export.js
 * Title: Export Page Controller
 * Description: Dynamically builds the export UI from graphs.json and triggers Python generation.
 * Author: Hugh Brennan
 * Date: 2026-04-30
 * Version: 0.1
 */

// import dependencies
import { API } from './api.js';
import { DOMUtils, NotificationManager } from './tools/utils.js';

/**
 * A centralized schema of DOM selectors that decouples the JavaScript logic 
 * from specific HTML IDs and classes, facilitating easier UI refactoring.
 */
const UI_SELECTORS = {
    checklistContainer: "dynamic-graph-checklist",
    exportBtn: "btn-run-export",
    statusText: "export-status"
};

/**
 * Manages the UI and API interactions for exporting dashboard graphs.
 */
class ExportController {
    static els = {};

    /**
     * Initializes the controller, maps DOM elements, and loads configurations.
     */
    static async init() {
        this.els = DOMUtils.mapElements(UI_SELECTORS);
        
        if (!this.els.checklistContainer || !this.els.exportBtn) {
            console.warn("[ExportController] Required DOM elements missing. Initialization aborted.");
            return;
        }

        this.bindEvents();
        await this.loadConfigurations();
    }

    /**
     * Fetches available graph configurations from the API and renders the checklist.
     */
    static async loadConfigurations() {
        try {
            // fetch available graphs from api
            const configs = await API.getExportConfig();

            // clear loading text
            this.els.checklistContainer.innerHTML = '';
            
            for (const [key, data] of Object.entries(configs)) {
                const row = document.createElement("div");
                row.className = "d-flex align-center gap-05";
                row.innerHTML = `
                    <input type="checkbox" class="export-chk" id="chk-${key}" value="${key}" checked> 
                    <label for="chk-${key}">${data.title} <span class="text-muted text-sm">(.png / .svg)</span></label>
                `;
                this.els.checklistContainer.appendChild(row);
            }
        } catch (error) {
            this.els.checklistContainer.innerHTML = '<span style="color: var(--error-color);">Failed to load configurations. Ensure backend is running.</span>';
            console.error("[Export Error] Failed to load configurations:", error);
        }
    }

    /**
     * Attaches event listeners for the export trigger button.
     */
    static bindEvents() {
        this.els.exportBtn.addEventListener("click", async () => {
            this.els.exportBtn.disabled = true;
            this.els.exportBtn.innerText = "Generating...";
            this.els.statusText.style.color = "var(--text-primary)";
            this.els.statusText.innerText = "Running Python DataExtractor... please wait.";

            // grab all checked boxes
            const selectedGraphs = Array.from(document.querySelectorAll('.export-chk:checked')).map(cb => cb.value);

            try {
                const result = await API.runExport({ selected_graphs: selectedGraphs });

                if (result.status === "success") {
                    this.els.statusText.style.color = "var(--success-color)";
                    this.els.statusText.innerText = "✅ " + result.message;
                    NotificationManager.show("Export completed successfully!");
                } else {
                    throw new Error("Backend reported export failure.");
                }
            } catch (error) {
                this.els.statusText.style.color = "var(--error-color)";
                this.els.statusText.innerText = "❌ An error occurred during export.";
                NotificationManager.show("Export failed. Check the server logs.", true);
                console.error("[Export Error]:", error);
            } finally {
                this.els.exportBtn.disabled = false;
                this.els.exportBtn.innerText = "Run Full Export";
            }
        });
    }
}

// execute controller on DOM load
document.addEventListener("DOMContentLoaded", () => ExportController.init());