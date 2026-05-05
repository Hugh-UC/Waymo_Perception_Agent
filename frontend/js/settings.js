/**
 * File: settings.js
 * Title: System Configuration Controller
 * Description: Manages the UI state, strict input validation, multi-tier saving 
 * (Cookie, JSON Backup, YAML config), desync reconciliation, and dynamic Datalists.
 * Author: Hugh Brennan
 * Date: 2026-04-24
 * Version: 0.1
 */

// import dependencies
import { API } from './api.js';
import { CookieUtils, NotificationManager, DOMUtils, DatalistManager } from './tools/utils.js';

// ---------------------------------------------------------
// DOM Selector Configuration Map
// ---------------------------------------------------------
/**
 * A centralized schema of DOM selectors that decouples the JavaScript logic 
 * from specific HTML IDs and classes, facilitating easier UI refactoring.
 */
const UI_SELECTORS = {
    global: {
        messageBox: "message-box",
        syncModal: "sync-modal",
        diffContainer: "diff-container",
        btnKeepBrowser: "btn-keep-browser",
        btnKeepProject: "btn-keep-project"
    },
    models: {
        agentInput: "agent-model",
        customContainerId: "custom-models-container"    // dynamically injected ID
    },
    users: {
        tbody: "users-tbody",
        roleSelect: "new-role",
        form: "add-user-form",
        usernameInput: "new-username",
        emailInput: "new-email",
        passwordInput: "new-password",
        jobInput: "new-job-title"
    },
    apiKeys: {
        saveBtn: "btn-save-apis",
        gemini: "env-gemini-key",
        news: "env-news-key",
        youtube: "env-yt-key",
        gcs: "env-gcs-key",
        cx: "env-gcs-cx"
    },
    config: {
        form: "settings-form",
        newsQuery: "news-query",
        newsDays: "news-days",
        newsMax: "news-max",
        redditMax: "reddit-max",
        subInput: "new-subreddit",
        subAddBtn: "btn-add-sub",
        subError: "sub-error",
        subTags: "subreddit-tags",
        fallbackInput: "new-fallback-model",
        fallbackAddBtn: "btn-add-fallback",
        fallbackError: "fallback-error",
        fallbackTags: "fallback-tags",
        agentTemp: "agent-temp",
        agentRetries: "agent-retries",
        agentOutRetries: "agent-out-retries"
    },
    navigation: {
        sidebarBtns: ".sidebar-btn",
        sections: ".settings-section"
    }
};


// ---------------------------------------------------------
// Domain Managers
// ---------------------------------------------------------
/**
 * Manages custom AI model datalist and dynamic tag rendering.
 */
class ModelManager {
    /**
     * Initializes the ModelManager, maps DOM elements, and sets safety defaults.
     * @param {Object} selectors - UI_SELECTORS.models configuration.
     */
    constructor(selectors) {
        // Cache DOM elements
        this.els = DOMUtils.mapElements(selectors);
        this.els.customContainer = null;        // will hold dynamically created container
        
        this.containerId = selectors.customContainerId;

        // Hardcoded AI Model Safety Defaults
        this.defaultModels = [
            "gemini-3.1-pro-preview",
            "gemini-3-flash-preview",
            "gemini-2.5-pro",
            "gemini-3.1-flash-lite-preview",
            "gemini-2.5-flash"
        ];

        if (!this.els.agentInput) {
            console.warn("[ModelManager] Target input 'agent-model' missing. Model management disabled.");
            return;
        }

        this.setupDOM();
    }

    /**
     * Dynamically injects custom model tag container into DOM if it doesn't exist.
     */
    setupDOM() {
        let container = document.getElementById(this.containerId);
        if (!container) {
            container = document.createElement("div");
            container.id = this.containerId;
            container.className = "tag-container";
            container.style.marginTop = "10px";
            this.els.agentInput.closest(".input-group").appendChild(container);
        }
        this.els.customContainer = container;
    }

    /**
     * Retrieves the list of user-defined custom models from localStorage.
     * @returns {string[]} array of custom model names.
     */
    getCustomModels() {
        return JSON.parse(localStorage.getItem("waymo_custom_models") || "[]");
    }

    /**
     * Adds new model to localStorage if it's not default model.
     * @param {string} model - model name to add.
     */
    add(model) {
        if (!model || this.defaultModels.includes(model)) return;
        const custom = this.getCustomModels();
        if (!custom.includes(model)) {
            custom.push(model);
            localStorage.setItem("waymo_custom_models", JSON.stringify(custom));
        }
    }

    /**
     * Removes custom model from localStorage and updates UI.
     * @param {string} model - model name to remove.
     */
    remove(model) {
        let custom = this.getCustomModels();
        custom = custom.filter(m => m !== model);
        localStorage.setItem("waymo_custom_models", JSON.stringify(custom));
        this.syncDatalists();
    }

    /**
     * Synchronizes global DatalistManager to include API models, default models, and custom models.
     */
    syncDatalists() {
        if (DatalistManager) {
            const apiModels = DatalistManager.availableModels || [];
            const allModels = new Set([...apiModels, ...this.defaultModels, ...this.getCustomModels()]);
            DatalistManager.availableModels = Array.from(allModels);
        }
        this.renderTags();
    }

    /**
     * Renders custom model tags into dynamically created DOM container.
     */
    renderTags() {
        if (!this.els.customContainer) {
            console.warn("[ModelManager] Custom container missing during render.");
            return;
        }
        
        this.els.customContainer.innerHTML = "";
        
        const custom = this.getCustomModels();
        if (custom.length === 0) return;

        const label = document.createElement("div");
        label.style.width = "100%";
        label.style.fontSize = "0.8rem";
        label.style.color = "var(--text-secondary)";
        label.textContent = "Custom Models (Click × to delete from dropdown):";
        this.els.customContainer.appendChild(label);

        custom.forEach(model => {
            const tag = document.createElement("div");
            tag.className = "tag";
            tag.style.backgroundColor = "var(--surface-hover)";
            tag.style.color = "var(--text-primary)";
            tag.style.border = "1px solid var(--border-color)";
            tag.innerHTML = `${model} <button type="button" data-model="${model}" style="color: var(--error-color);">×</button>`;
            
            // attach event listener to button
            const btn = tag.querySelector("button");
            if(btn) btn.addEventListener("click", (e) => this.remove(e.target.dataset.model));
            
            this.els.customContainer.appendChild(tag);
        });
    }
}


/**
 * Manages User Administration panel, including creation and deletion of accounts.
 */
class UserManager {
    /**
     * Initializes the UserManager and maps UI elements.
     * @param {Object} selectors - UI_SELECTORS.users configuration.
     */
    constructor(selectors) {
        // automatically map all selector strings to DOM elements
        this.els = DOMUtils.mapElements(selectors);

        // graceful degradation check
        if (!this.els.tbody || !this.els.form || !this.els.roleSelect) {
            console.warn("[UserManager] Required DOM elements missing. User management disabled.");
            return;
        }

        this.bindEvents();
    }

    /**
     * Attaches event listeners for user creation forms.
     */
    bindEvents() {
        this.els.form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const payload = {
                username: this.els.usernameInput.value,
                email: this.els.emailInput.value,
                password: this.els.passwordInput.value,
                role: this.els.roleSelect.value,
                job_title: this.els.jobInput.value
            };

            try {
                await API.addUser(payload);
                this.els.form.reset();
                await this.load();
                NotificationManager.show("User created successfully!");
            } catch (error) {
                NotificationManager.show(error.detail || "Failed to create user.", true);
            }
        });
    }

    /**
     * Fetches user/role data from the backend and populates the management table.
     */
    async load() {
        try {
            // Populate roles dropdown
            const rolesData = await API.getRoles();
            if(rolesData && rolesData.roles) {
                 this.els.roleSelect.innerHTML = "";
                 for (const [key, role] of Object.entries(rolesData.roles)) {
                     const option = document.createElement("option");
                     option.value = key;
                     option.textContent = role.display_name;
                     this.els.roleSelect.appendChild(option);
                 }
            }

            // Populate users table
            const users = await API.getUsers();
            this.els.tbody.innerHTML = "";
            users.forEach(user => {
                const tr = document.createElement("tr");
                tr.style.borderBottom = "1px solid var(--border-color)";
                
                const loginDate = user.last_login ? new Date(user.last_login).toLocaleString() : "Never";
                const isMasterAdmin = user.id === 1;

                tr.innerHTML = `
                    <td><strong>${user.username}</strong><br><small class="text-muted">${user.email}</small></td>
                    <td><span class="role-badge">${user.role}</span></td>
                    <td style="font-size: 0.9rem;">${loginDate}</td>
                    <td>
                        ${!isMasterAdmin ? `<button class="btn-delete-user" data-id="${user.id}">Delete</button>` : '<span class="text-muted text-sm">Protected</span>'}
                    </td>
                `;
                
                // Attach delete listeners
                const deleteBtn = tr.querySelector('.btn-delete-user');
                if (deleteBtn) {
                    deleteBtn.addEventListener('click', async (e) => {
                        if (confirm("Are you sure you want to permanently delete this user?")) {
                            try {
                                await API.deleteUser(e.target.dataset.id);
                                NotificationManager.show("User deleted successfully.");
                                await this.load();      // refresh table
                            } catch (error) {
                                NotificationManager.show(error.detail || "Failed to delete user.", true);
                            }
                        }
                    });
                }
                this.els.tbody.appendChild(tr);
            });
        } catch (error) {
            console.error("Failed to load user management data:", error);
        }
    }
}


/**
 * Manages securely masked API key configurations and .env updates.
 */
class ApiKeyManager {
    /**
     * Initializes the ApiKeyManager and maps UI elements.
     * @param {Object} selectors - UI_SELECTORS.apiKeys configuration.
     */
    constructor(selectors) {
        // automatically map all selector strings to DOM elements
        this.els = DOMUtils.mapElements(selectors);

        if (!this.els.saveBtn) {
            console.warn("[ApiKeyManager] Save button missing. API Key management disabled.");
            return;
        }
        this.bindEvents();
    }

    /**
     * Attaches event listeners for the API Key save button.
     */
    bindEvents() {
        this.els.saveBtn.addEventListener("click", async (e) => {
            const btn = e.target;
            btn.textContent = "Saving...";
            btn.disabled = true;

            const payload = {
                gemini_key: this.els.gemini?.value.trim() || "",
                news_key: this.els.news?.value.trim() || "",
                youtube_key: this.els.youtube?.value.trim() || "",
                gcs_key: this.els.gcs?.value.trim() || "",
                gcs_cx: this.els.cx?.value.trim() || ""
            };

            try {
                await API.setupKeys(payload);
                NotificationManager.show("API Keys updated successfully!");
                await this.load();
            } catch (error) {
                NotificationManager.show("Network Error: Could not save API keys.", true);
            } finally {
                btn.textContent = "Save Environment Keys";
                btn.disabled = false;
            }
        });
    }

    /**
     * Fetches masked API key states from backend to populate UI.
     */
    async load() {
        try {
            const status = await API.getStatus();
            if (status.masked_gemini && this.els.gemini) this.els.gemini.value = status.masked_gemini;
            if (status.masked_news && this.els.news) this.els.news.value = status.masked_news;
            if (status.masked_yt && this.els.youtube) this.els.youtube.value = status.masked_yt;
            if (status.masked_gcs && this.els.gcs) this.els.gcs.value = status.masked_gcs;
            if (status.masked_cx && this.els.cx) this.els.cx.value = status.masked_cx;
        } catch (error) {
            console.error("Failed to load masked API keys:", error);
        }
    }
}


/**
 * Core Configuration Manager handling complex params.yaml sync, diffs, and fallback models.
 */
class ConfigManager {
    /**
     * Initializes the ConfigManager with dependencies and required UI elements.
     * @param {Object} selectors - UI_SELECTORS.config dictionary.
     * @param {ModelManager} modelManager - instance of the ModelManager class.
     * @param {Object} globalSelectors - UI_SELECTORS.global dictionary for modal targeting.
     */
    constructor(selectors, modelManager, globalSelectors) {
        this.modelManager = modelManager;
        this.state = { subreddits: [], fallbackModels: [] };
        this.MAX_SUBREDDITS = 16;
        this.actualProjectConfig = null;
        this.latestSavedConfig = null;
        
        // Map all primary form selectors
        this.els = DOMUtils.mapElements(selectors);

        // Manually inject globals
        this.els.syncModal          = document.getElementById(globalSelectors.syncModal);
        this.els.diffContainer      = document.getElementById(globalSelectors.diffContainer);
        this.els.btnKeepBrowser     = document.getElementById(globalSelectors.btnKeepBrowser);
        this.els.btnKeepProject     = document.getElementById(globalSelectors.btnKeepProject);
        this.els.agentModelInput    = document.getElementById(UI_SELECTORS.models.agentInput);

        if (!this.els.form) {
            console.warn("[ConfigManager] Core config form missing. Initialisation aborted.");
            return;
        }
        this.bindEvents();
    }

    /**
     * Attaches event listeners for form submission, tag addition, and desync modal resolution.
     */
    bindEvents() {
        this.els.subAddBtn?.addEventListener("click", () => this.addSubreddit());
        this.els.fallbackAddBtn?.addEventListener("click", () => this.addFallback());
        this.els.form.addEventListener("submit", (e) => this.handleSave(e));

        this.els.btnKeepBrowser?.addEventListener("click", async () => {
            if(this.els.syncModal) this.els.syncModal.classList.add("hidden");
            this.populateForm(this.latestSavedConfig);
            await this.saveToProjectFile(this.latestSavedConfig); 
            NotificationManager.show("Project files updated to match your browser preferences.");
        });

        this.els.btnKeepProject?.addEventListener("click", async () => {
            if(this.els.syncModal) this.els.syncModal.classList.add("hidden");
            this.populateForm(this.actualProjectConfig);
            await this.updateBackups(this.actualProjectConfig); 
            NotificationManager.show("Browser preferences updated to match project files.");
        });
    }

    /**
     * Bootstraps datalists, fetches configs, and handles desync resolution.
     */
    async initialize() {
        try {
            if (DatalistManager) {
                await DatalistManager.initialize(API);
                this.modelManager.syncDatalists();
                DatalistManager.setup(UI_SELECTORS.models.agentInput, "settings-primary-list");
                DatalistManager.setup(UI_SELECTORS.config.fallbackInput, "settings-fallback-list");
            }

            this.actualProjectConfig = await API.getConfig();
            const jsonPrefs = await API.getPreferences();
            const cookiePrefs = CookieUtils.get("waymo_agent_prefs");

            const jsonTime = jsonPrefs.timestamp || 0;
            const cookieTime = cookiePrefs ? cookiePrefs.timestamp : 0;
            
            if (jsonTime === 0 && cookieTime === 0) {
                this.populateForm(this.actualProjectConfig);
                return;
            }

            const bestPrefs = (cookieTime > jsonTime) ? cookiePrefs.config : jsonPrefs.config;
            this.latestSavedConfig = bestPrefs;

            const diffs = this.findDifferences(this.actualProjectConfig, bestPrefs);
            
            if (diffs.length > 0 && this.els.syncModal && this.els.diffContainer) {
                this.els.diffContainer.innerHTML = diffs.map(d => `<div style="margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color);">${d}</div>`).join("");
                this.els.syncModal.classList.remove("hidden");
            } else {
                this.populateForm(this.actualProjectConfig);
            }
        } catch (e) {
            NotificationManager.show("System Error: Failed to initialize configuration settings.", true);
            console.error(e);
        }
    }

    /**
     * Recursively computes the differences between project YAML and browser saved configurations.
     * @param {Object} project - config pulled from params.yaml.
     * @param {Object} saved - config pulled from the browser backup.
     * @param {string} [path=""] - hierarchical path for logging.
     * @returns {string[]} array of formatted HTML strings detailing the differences.
     */
    findDifferences(project, saved, path = "") {
        let diffs = [];
        if (!project || !saved) return diffs; 

        const keys = new Set([...Object.keys(project), ...Object.keys(saved)]);
        
        keys.forEach(key => {
            const projVal = project[key];
            const saveVal = saved[key];
            const currentPath = path ? `${path}.${key}` : key;

            if (Array.isArray(projVal) && Array.isArray(saveVal)) {
                if (JSON.stringify(projVal) !== JSON.stringify(saveVal)) {
                    diffs.push(`<b>${currentPath}</b>:<br>Project YAML: [${projVal}]<br>Browser Saved: [${saveVal}]`);
                }
            } else if (typeof projVal === "object" && typeof saveVal === "object" && projVal !== null && saveVal !== null) {
                diffs = diffs.concat(this.findDifferences(projVal, saveVal, currentPath));
            } else if (projVal !== saveVal) {
                diffs.push(`<b>${currentPath}</b>:<br>Project YAML: ${projVal}<br>Browser Saved: ${saveVal}`);
            }
        });
        return diffs;
    }

    /**
     * Hydrates UI form elements based on provided configuration object.
     * @param {Object} config - structured configuration object.
     */
    populateForm(config) {
        if (!config || !config.scraper || !config.agent) {
             console.warn("[ConfigManager] Invalid configuration object provided to populateForm.");
             return;
        }

        if(this.els.newsQuery) this.els.newsQuery.value = config.scraper.news.query;
        if(this.els.newsDays) this.els.newsDays.value = config.scraper.news.days_back;
        if(this.els.newsMax) this.els.newsMax.value = config.scraper.news.max_articles;
        if(this.els.redditMax) this.els.redditMax.value = config.scraper.reddit.max_posts;
        
        this.state.subreddits = config.scraper.reddit.subreddit || [];
        this.renderTags(this.els.subTags, this.state.subreddits, "sub");

        const primaryModel = config.agent.model_name;
        if(this.els.agentModelInput) this.els.agentModelInput.value = primaryModel;
        this.modelManager.add(primaryModel);

        this.state.fallbackModels = config.agent.fallback_model || [];
        this.state.fallbackModels.forEach(m => this.modelManager.add(m));

        this.modelManager.syncDatalists();
        this.renderTags(this.els.fallbackTags, this.state.fallbackModels, "fallback");

        if(this.els.agentTemp) this.els.agentTemp.value = config.agent.temperature;
        if(this.els.agentRetries) this.els.agentRetries.value = config.agent.retries;
        if(this.els.agentOutRetries) this.els.agentOutRetries.value = config.agent.output_retries;
    }

    /**
     * Renders a dynamic array of text tags into a specified container.
     * @param {HTMLElement} containerEl - DOM element to render tags into.
     * @param {string[]} dataArray - array of strings to render.
     * @param {string} type - identifier ("sub" or "fallback") to format output.
     */
    renderTags(containerEl, dataArray, type) {
        if (!containerEl) {
             console.warn(`[ConfigManager] Tag container missing for type: ${type}`);
             return;
        }
        containerEl.innerHTML = "";

        dataArray.forEach((item, index) => {
            const tag = document.createElement("div");
            tag.className = "tag";
            tag.innerHTML = `${type === "sub" ? "r/" : ""}${item} <button type="button" data-index="${index}">×</button>`;
            
            const btn = tag.querySelector("button");
            if(btn) {
                btn.addEventListener("click", (e) => {
                    dataArray.splice(e.target.dataset.index, 1);
                    this.renderTags(containerEl, dataArray, type);
                });
            }
            containerEl.appendChild(tag);
        });
    }

    /**
     * Validates and adds new subreddit to scraping target list.
     */
    addSubreddit() {
        if(!this.els.subError || !this.els.subInput) return;

        this.els.subError.classList.add("hidden");
        const val = this.els.subInput.value.trim();

        if (this.state.subreddits.length >= this.MAX_SUBREDDITS) {
            this.els.subError.textContent = `Maximum limit of ${this.MAX_SUBREDDITS} subreddits reached.`;
            this.els.subError.classList.remove("hidden");
            return;
        }

        if (!/^[A-Za-z0-9_]{3,21}$/.test(val)) {
            this.els.subError.textContent = "Invalid name. Must be 3-21 characters, letters, numbers, or underscores only.";
            this.els.subError.classList.remove("hidden");
            return;
        }

        if (this.state.subreddits.includes(val)) {
            this.els.subError.textContent = "This subreddit is already currently in the target list.";
            this.els.subError.classList.remove("hidden");
            return;
        }

        this.state.subreddits.push(val);
        this.els.subInput.value = "";
        this.renderTags(this.els.subTags, this.state.subreddits, "sub");
    }

    /**
     * Validates and adds new fallback model to configuration state.
     */
    addFallback() {
        if(!this.els.fallbackError || !this.els.fallbackInput) return;

        this.els.fallbackError.classList.add("hidden");
        const val = this.els.fallbackInput.value.trim();

        if (!val) return;
        if (this.state.fallbackModels.includes(val)) {
            this.els.fallbackError.textContent = "Model is already in the fallback list.";
            this.els.fallbackError.classList.remove("hidden");
            return;
        }

        this.state.fallbackModels.push(val);
        this.modelManager.add(val);
        this.modelManager.syncDatalists();
        this.renderTags(this.els.fallbackTags, this.state.fallbackModels, "fallback");
        this.els.fallbackInput.value = "";
    }

    /**
     * Compiles form data into structured payload and sends to API.
     * @param {Event} e - form submission event.
     */
    async handleSave(e) {
        e.preventDefault();
        
        let primaryModel = "";
        if(this.els.agentModelInput) {
             primaryModel = this.els.agentModelInput.value.trim();
             this.modelManager.add(primaryModel);
             this.modelManager.syncDatalists();
        }

        const payload = {
            scraper: {
                news: {
                    query: this.els.newsQuery ? this.els.newsQuery.value : "",
                    days_back: this.els.newsDays ? parseFloat(this.els.newsDays.value) : 0,
                    max_articles: this.els.newsMax ? parseInt(this.els.newsMax.value) : 0
                },
                reddit: {
                    subreddit: this.state.subreddits,
                    max_posts: this.els.redditMax ? parseInt(this.els.redditMax.value) : 0
                }
            },
            agent: {
                model_name: primaryModel,
                fallback_model: this.state.fallbackModels,
                temperature: this.els.agentTemp ? parseFloat(this.els.agentTemp.value) : 0.2,
                retries: this.els.agentRetries ? parseInt(this.els.agentRetries.value) : 3,
                output_retries: this.els.agentOutRetries ? parseInt(this.els.agentOutRetries.value) : 5
            }
        };

        const success = await this.saveToProjectFile(payload);
        if (success) {
            await this.updateBackups(payload);
            NotificationManager.show("Configuration synchronised across all systems successfully!");
        }
    }

    /**
     * Dispatches configuration payload to backend to rewrite params.yaml.
     * @param {Object} payload - configuration dictionary.
     * @returns {Promise<boolean>} true if successful, false otherwise.
     */
    async saveToProjectFile(payload) {
        try {
            await API.updateConfig(payload);
            return true;
        } catch (error) {
            NotificationManager.show("Network Error: Could not save configuration to project files.", true);
            console.error(error);
            return false;
        }
    }

    /**
     * Saves secondary backup of config to settings.json and browser cookies.
     * @param {Object} payload - configuration dictionary.
     */
    async updateBackups(payload) {
        const backupData = { timestamp: Date.now(), config: payload };
        CookieUtils.set("waymo_agent_prefs", backupData, 30);
        try {
            await API.savePreferences(backupData);
        } catch (error) {
            console.error("[Backup Error] Failed to update settings.json:", error);
        }
    }
}


// ---------------------------------------------------------
// Master Orchestrator
// ---------------------------------------------------------
/**
 * Acts as the primary orchestrator for the Settings page, initializing managers and navigation.
 */
class SettingsDashboard {
    /**
     * Main entry point to initialize sidebar navigation and domain-specific managers.
     */
    static init() {
        const sidebarBtns = document.querySelectorAll(UI_SELECTORS.navigation.sidebarBtns);
        const sections = document.querySelectorAll(UI_SELECTORS.navigation.sections);

        sidebarBtns.forEach(btn => {
            btn.addEventListener("click", () => {
                sidebarBtns.forEach(b => b.classList.remove("active"));
                sections.forEach(s => s.classList.add("hidden"));
                btn.classList.add("active");
                
                const targetId = btn.dataset.target || btn.getAttribute('data-target'); 
                if(targetId) {
                    const target = document.getElementById(targetId);
                    if (target) target.classList.remove("hidden");
                }
            });
        });

        // Initialize Managers with injected config dependencies
        const modelManager = new ModelManager(UI_SELECTORS.models);
        const configManager = new ConfigManager(UI_SELECTORS.config, modelManager, UI_SELECTORS.global);
        const userManager = new UserManager(UI_SELECTORS.users);
        const apiKeyManager = new ApiKeyManager(UI_SELECTORS.apiKeys);

        // Boot Sequence
        if (configManager.els.form) configManager.initialize();
        if (userManager.els.tbody) userManager.load();
        if (apiKeyManager.els.saveBtn) apiKeyManager.load();
    }
}

// Execute on DOM Load
document.addEventListener("DOMContentLoaded", SettingsDashboard.init);