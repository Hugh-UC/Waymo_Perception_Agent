/**
 * File: datalist.js
 * Title: Custom Datalist UI Controller
 * Description: Manages the fetching of available AI models and binds custom 
 * searchable dropdown logic to standard text inputs.
 * Author: Hugh Brennan
 * Date: 2026-04-24
 * Version: 0.1
 */

const DatalistManager = {
    availableModels: [],

    /**
     * Fetches the model registry from the backend to populate dropdowns.
     */
    async initialize() {
        try {
            const data = await window.API.getModels();
            this.availableModels = data.models;
        } catch (error) {
            console.error("Failed to load models list:", error);
        }
    },

    /**
     * Binds the custom dropdown logic to a specific input and list element.
     * @param {string} inputId - The ID of the text input.
     * @param {string} listId - The ID of the hidden unordered list.
     */
    setup(inputId, listId) {
        const input = document.getElementById(inputId);
        const list = document.getElementById(listId);
        if (!input || !list) return;

        const renderList = (filterText = "") => {
            list.innerHTML = "";
            const filtered = this.availableModels.filter(m => 
                m.toLowerCase().includes(filterText.toLowerCase())
            );
            
            filtered.forEach(model => {
                const li = document.createElement("li");
                li.textContent = model;
                
                // mousedown fires before blur, allowing us to capture the click
                li.addEventListener("mousedown", (e) => {
                    e.preventDefault(); 
                    input.value = model;
                    list.classList.add("hidden");
                });
                list.appendChild(li);
            });
        };

        // Event Listeners
        input.addEventListener("focus", () => { 
            renderList(input.value); 
            list.classList.remove("hidden"); 
        });
        input.addEventListener("input", (e) => renderList(e.target.value));
        input.addEventListener("blur", () => list.classList.add("hidden"));
    }
};

// Expose to global window object
window.DatalistManager = DatalistManager;