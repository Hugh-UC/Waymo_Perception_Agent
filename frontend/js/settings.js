/**
 * File: settings.js
 * Title: System Configuration Controller
 * Description: Manages the UI state, strict input validation, multi-tier saving 
 * (Cookie, JSON Backup, YAML config), desync reconciliation, and dynamic Datalists.
 * Author: Hugh Brennan
 * Date: 2026-04-22
 * Version: 0.1
 */

document.addEventListener("DOMContentLoaded", async () => {
    // ---------------------------------------------------------
    // 1. Global State Variables
    // ---------------------------------------------------------
    let currentSubreddits = [];
    let currentFallbackModels = [];
    const MAX_SUBREDDITS = 16;
    let actualProjectConfig = null;
    let latestSavedConfig = null;

    // Hardcoded safety defaults
    const defaultModels = [
        "gemini-3.1-pro-preview",
        "gemini-3-flash-preview",
        "gemini-2.5-pro",
        "gemini-3.1-flash-lite-preview",
        "gemini-2.5-flash"
    ];

    // UI Elements
    const tagContainer = document.getElementById("subreddit-tags");
    const subInput = document.getElementById("new-subreddit");
    const addSubBtn = document.getElementById("btn-add-sub");
    const subError = document.getElementById("sub-error");
    const statusBox = document.getElementById("save-status");
    const syncModal = document.getElementById("sync-modal");
    const diffContainer = document.getElementById("diff-container");

    // ---------------------------------------------------------
    // 2. Dynamic Custom Model Datalist Manager
    // ---------------------------------------------------------

    // Inject a container below the Primary Model select to manage Custom options
    const agentModelInput = document.getElementById("agent-model");
    if (agentModelInput) {
        let customDiv = document.createElement("div");
        customDiv.id = "custom-models-container";
        customDiv.className = "tag-container";
        customDiv.style.marginTop = "10px";
        agentModelInput.parentElement.appendChild(customDiv);
    }

    function getCustomModels() {
        return JSON.parse(localStorage.getItem("waymo_custom_models") || "[]");
    }

    function addCustomModel(model) {
        if (!model || defaultModels.includes(model)) return;
        const custom = getCustomModels();
        if (!custom.includes(model)) {
            custom.push(model);
            localStorage.setItem("waymo_custom_models", JSON.stringify(custom));
        }
    }

    function removeCustomModel(model) {
        let custom = getCustomModels();
        custom = custom.filter(m => m !== model);
        localStorage.setItem("waymo_custom_models", JSON.stringify(custom));
        updateModelDatalists();
    }

    function updateModelDatalists() {
        const datalist = document.getElementById("model-options-list");
        if (!datalist) return;
        datalist.innerHTML = ""; 
        
        // Merge hardcoded defaults with user's custom additions
        const allModels = new Set([...defaultModels, ...getCustomModels()]);

        allModels.forEach(model => {
            const option = document.createElement("option");
            option.value = model;
            datalist.appendChild(option);
        });

        renderCustomModelTags();
    }

    function renderCustomModelTags() {
        const container = document.getElementById("custom-models-container");
        if (!container) return;
        container.innerHTML = "";
        
        const custom = getCustomModels();
        if (custom.length === 0) return;

        const label = document.createElement("div");
        label.style.width = "100%";
        label.style.fontSize = "0.8rem";
        label.style.color = "var(--text-secondary)";
        label.textContent = "Custom Models (Click × to delete from dropdown):";
        container.appendChild(label);

        custom.forEach(model => {
            const tag = document.createElement("div");
            tag.className = "tag";
            tag.style.backgroundColor = "var(--surface-hover)";
            tag.style.color = "var(--text-primary)";
            tag.style.border = "1px solid var(--border-color)";
            tag.innerHTML = `${model} <button type="button" data-model="${model}" style="color: var(--error-color);">×</button>`;
            container.appendChild(tag);
        });

        container.querySelectorAll("button").forEach(btn => {
            btn.addEventListener("click", (e) => {
                removeCustomModel(e.target.getAttribute("data-model"));
            });
        });
    }

    // ---------------------------------------------------------
    // 3. UI Navigation Logic (Google-Style Sidebar)
    // ---------------------------------------------------------
    const sidebarBtns = document.querySelectorAll(".sidebar-btn");
    const sections = document.querySelectorAll(".settings-section");

    sidebarBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            sidebarBtns.forEach(b => b.classList.remove("active"));
            sections.forEach(s => s.classList.add("hidden"));
            btn.classList.add("active");
            document.getElementById(btn.getAttribute("data-target")).classList.remove("hidden");
        });
    });

    // ---------------------------------------------------------
    // 4. Cookie Utilities
    // ---------------------------------------------------------
    function setCookie(name, value, days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        document.cookie = name + "=" + (JSON.stringify(value) || "") + "; expires=" + date.toUTCString() + "; path=/";
    }

    function getCookie(name) {
        const nameEQ = name + "=";
        const ca = document.cookie.split(';');
        for(let i=0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0)==' ') c = c.substring(1,c.length);
            if (c.indexOf(nameEQ) == 0) return JSON.parse(c.substring(nameEQ.length,c.length));
        }
        return null;
    }

    // ---------------------------------------------------------
    // 5. Data Reconciliation Engine
    // ---------------------------------------------------------
    function findDifferences(project, saved, path = "") {
        let diffs = [];
        const keys = new Set([...Object.keys(project), ...Object.keys(saved)]);
        
        keys.forEach(key => {
            const projVal = project[key];
            const saveVal = saved[key];
            const currentPath = path ? `${path}.${key}` : key;

            if (Array.isArray(projVal) && Array.isArray(saveVal)) {
                if (JSON.stringify(projVal) !== JSON.stringify(saveVal)) {
                    diffs.push(`<b>${currentPath}</b>:<br>Project YAML: [${projVal}]<br>Browser Saved: [${saveVal}]`);
                }
            } else if (typeof projVal === "object" && typeof saveVal === "object") {
                diffs = diffs.concat(findDifferences(projVal, saveVal, currentPath));
            } else if (projVal !== saveVal) {
                diffs.push(`<b>${currentPath}</b>:<br>Project YAML: ${projVal}<br>Browser Saved: ${saveVal}`);
            }
        });
        return diffs;
    }

    async function initializeSettings() {
        try {
            const configRes = await fetch("/api/config");
            actualProjectConfig = await configRes.json();
            const prefsRes = await fetch("/api/preferences");
            const jsonPrefs = await prefsRes.json();
            const cookiePrefs = getCookie("waymo_agent_prefs");

            const jsonTime = jsonPrefs.timestamp || 0;
            const cookieTime = cookiePrefs ? cookiePrefs.timestamp : 0;
            
            if (jsonTime === 0 && cookieTime === 0) {
                populateForm(actualProjectConfig);
                return;
            }

            const bestPrefs = (cookieTime > jsonTime) ? cookiePrefs.config : jsonPrefs.config;
            latestSavedConfig = bestPrefs;

            const diffs = findDifferences(actualProjectConfig, bestPrefs);
            
            if (diffs.length > 0) {
                diffContainer.innerHTML = diffs.map(d => `<div style="margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color);">${d}</div>`).join("");
                syncModal.classList.remove("hidden");
            } else {
                populateForm(actualProjectConfig);
            }
        } catch (e) {
            showStatus("System Error: Failed to initialize configuration settings.", true);
            console.error(e);
        }
    }

    document.getElementById("btn-keep-browser").addEventListener("click", async () => {
        syncModal.classList.add("hidden");
        populateForm(latestSavedConfig);
        await saveToProjectFile(latestSavedConfig); 
        showStatus("Project files updated to match your browser preferences.", false);
    });

    document.getElementById("btn-keep-project").addEventListener("click", async () => {
        syncModal.classList.add("hidden");
        populateForm(actualProjectConfig);
        await updateBackups(actualProjectConfig); 
        showStatus("Browser preferences updated to match project files.", false);
    });

    // ---------------------------------------------------------
    // 6. UI Rendering & Input Management
    // ---------------------------------------------------------
    function populateForm(config) {
        // Scraper Mapping
        document.getElementById("news-query").value = config.scraper.news.query;
        document.getElementById("news-days").value = config.scraper.news.days_back;
        document.getElementById("news-max").value = config.scraper.news.max_articles;
        document.getElementById("reddit-max").value = config.scraper.reddit.max_posts;
        currentSubreddits = config.scraper.reddit.subreddit || [];
        renderTags();

        // Agent Mapping
        const primaryModel = config.agent.model_name;
        document.getElementById("agent-model").value = primaryModel;
        addCustomModel(primaryModel);

        currentFallbackModels = config.agent.fallback_model || [];
        currentFallbackModels.forEach(m => addCustomModel(m));

        updateModelDatalists();
        renderFallbackTags();

        document.getElementById("agent-temp").value = config.agent.temperature;
        document.getElementById("agent-retries").value = config.agent.retries;
        document.getElementById("agent-out-retries").value = config.agent.output_retries;
    }

    function renderTags() {
        tagContainer.innerHTML = "";
        currentSubreddits.forEach((sub, index) => {
            const tag = document.createElement("div");
            tag.className = "tag";
            tag.innerHTML = `r/${sub} <button type="button" data-index="${index}">×</button>`;
            tagContainer.appendChild(tag);
        });

        tagContainer.querySelectorAll("button").forEach(btn => {
            btn.addEventListener("click", (e) => {
                currentSubreddits.splice(e.target.getAttribute("data-index"), 1);
                renderTags();
            });
        });
    }

    addSubBtn.addEventListener("click", () => {
        subError.classList.add("hidden");
        const newSub = subInput.value.trim();

        if (currentSubreddits.length >= MAX_SUBREDDITS) {
            subError.textContent = `Maximum limit of ${MAX_SUBREDDITS} subreddits reached.`;
            subError.classList.remove("hidden");
            return;
        }

        const redditRegex = /^[A-Za-z0-9_]{3,21}$/;
        if (!redditRegex.test(newSub)) {
            subError.textContent = "Invalid name. Must be 3-21 characters, letters, numbers, or underscores only.";
            subError.classList.remove("hidden");
            return;
        }

        if (currentSubreddits.includes(newSub)) {
            subError.textContent = "This subreddit is already currently in the target list.";
            subError.classList.remove("hidden");
            return;
        }

        currentSubreddits.push(newSub);
        subInput.value = "";
        renderTags();
    });

    // Render Fallback Tags
    function renderFallbackTags() {
        const container = document.getElementById("fallback-tags");
        if(!container) return;
        container.innerHTML = "";
        
        currentFallbackModels.forEach((model, index) => {
            const tag = document.createElement("div");
            tag.className = "tag";
            tag.innerHTML = `${model} <button type="button" data-index="${index}">×</button>`;
            container.appendChild(tag);
        });
        
        container.querySelectorAll("button").forEach(btn => {
            btn.addEventListener("click", (e) => {
                currentFallbackModels.splice(e.target.getAttribute("data-index"), 1);
                renderFallbackTags();
            });
        });
    }

    // Add Fallback Event
    document.getElementById("btn-add-fallback")?.addEventListener("click", () => {
        const input = document.getElementById("new-fallback-model");
        const errBox = document.getElementById("fallback-error");
        errBox.classList.add("hidden");
        const val = input.value.trim();

        if (!val) return;
        if (currentFallbackModels.includes(val)) {
            errBox.textContent = "Model is already in the fallback list.";
            errBox.classList.remove("hidden");
            return;
        }

        currentFallbackModels.push(val);
        addCustomModel(val);
        updateModelDatalists();
        renderFallbackTags();
        input.value = "";
    });

    // ---------------------------------------------------------
    // 7. Data Saving & API Submission
    // ---------------------------------------------------------
    document.getElementById("settings-form").addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const primaryModel = document.getElementById("agent-model").value.trim();
        addCustomModel(primaryModel);
        updateModelDatalists();

        const payload = {
            scraper: {
                news: {
                    query: document.getElementById("news-query").value,
                    days_back: parseFloat(document.getElementById("news-days").value),
                    max_articles: parseInt(document.getElementById("news-max").value)
                },
                reddit: {
                    subreddit: currentSubreddits,
                    max_posts: parseInt(document.getElementById("reddit-max").value)
                }
            },
            agent: {
                model_name: primaryModel,
                fallback_model: currentFallbackModels,
                temperature: parseFloat(document.getElementById("agent-temp").value),
                retries: parseInt(document.getElementById("agent-retries").value),
                output_retries: parseInt(document.getElementById("agent-out-retries").value)
            }
        };

        const success = await saveToProjectFile(payload);
        if (success) {
            await updateBackups(payload);
            showStatus("Configuration synchronised across all systems successfully!", false);
        }
    });

    async function saveToProjectFile(payload) {
        try {
            const response = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            if (!response.ok) throw new Error("Backend failed to write to params.yaml");
            return true;
        } catch (error) {
            showStatus("Network Error: Could not save configuration to project files.", true);
            console.error(error);
            return false;
        }
    }

    async function updateBackups(payload) {
        const timestamp = Date.now();
        const backupData = { timestamp: timestamp, config: payload };
        setCookie("waymo_agent_prefs", backupData, 30);

        try {
            await fetch("/api/preferences", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(backupData)
            });
        } catch (error) {
            console.error("[Backup Error] Failed to update settings.json:", error);
        }
    }

    function showStatus(message, isError) {
        statusBox.textContent = message;
        statusBox.style.backgroundColor = isError ? "var(--error-bg)" : "var(--success-bg)";
        statusBox.style.color = isError ? "var(--error-color)" : "var(--success-text)";
        statusBox.classList.remove("hidden");
        
        setTimeout(() => {
            statusBox.classList.add("hidden");
        }, 4000);
    }

    initializeSettings();
});