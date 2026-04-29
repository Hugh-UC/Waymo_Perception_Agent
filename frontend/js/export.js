/**
 * File: export.js
 * Title: Export Page Controller
 * Description: Dynamically builds the export UI from graphs.json and triggers Python generation.
 */
document.addEventListener("DOMContentLoaded", async () => {
    const checklistContainer = document.getElementById("dynamic-graph-checklist");
    const exportBtn          = document.getElementById("btn-run-export");
    const statusText         = document.getElementById("export-status");

    // 1. fetch available graphs from api
    try {
        const response = await fetch('/api/export/config');
        const configs  = await response.json();
        
        checklistContainer.innerHTML = '';      // clear loading text
        
        for (const [key, data] of Object.entries(configs)) {
            const row = document.createElement("div");

            row.className = "d-flex align-center gap-05";
            row.innerHTML = `
                <input type="checkbox" class="export-chk" id="chk-${key}" value="${key}" checked> 
                <label for="chk-${key}">${data.title} <span class="text-muted text-sm">(.png / .svg)</span></label>
            `;

            checklistContainer.appendChild(row);
        }
    } catch (error) {
        checklistContainer.innerHTML = '<span style="color: var(--error-color);">Failed to load configurations. Ensure backend is running.</span>';
    }

    // 2. handle export trigger
    exportBtn.addEventListener("click", async () => {
        exportBtn.disabled = true;
        exportBtn.innerText = "Generating...";
        statusText.style.color = "var(--text-primary)";
        statusText.innerText = "Running Python DataExtractor... please wait.";

        // grab all checked boxes
        const selectedGraphs = Array.from(document.querySelectorAll('.export-chk:checked')).map(cb => cb.value);

        try {
            const response = await fetch('/api/export/run', { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ selected_graphs: selectedGraphs })
            });
            const result = await response.json();

            if (result.status === "success") {
                statusText.style.color = "var(--success-color)";
                statusText.innerText = "✅ " + result.message;
            } else {
                throw new Error("Export failed");
            }
        } catch (error) {
            statusText.style.color = "var(--error-color)";
            statusText.innerText = "❌ An error occurred during export.";
        } finally {
            exportBtn.disabled = false;
            exportBtn.innerText = "Run Full Export";
        }
    });
});