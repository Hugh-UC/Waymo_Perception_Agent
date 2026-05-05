/**
 * File: utils.js
 * Title: Global Frontend Utilities
 * Description: Standalone helper classes for managing cookies, DOM notifications, and generic system logic.
 * Author: Hugh Brennan
 * Date: 2026-05-04
 * Version: 0.1
 */

// ---------------------------------------------------------
// Browser Data Utilities
// ---------------------------------------------------------
export class CookieUtils {
    /**
     * Sets a browser cookie with a specified expiration.
     * @param {string} name - The key name of the cookie.
     * @param {any} value - The value to store (will be JSON stringified).
     * @param {number} days - Number of days until the cookie expires.
     */
    static set(name, value, days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        document.cookie = `${name}=${JSON.stringify(value) || ""}; expires=${date.toUTCString()}; path=/`;
    }

    /**
     * Retrieves and parses a JSON cookie.
     * @param {string} name - The key name of the cookie.
     * @returns {any|null} The parsed JSON object, or null if not found.
     */
    static get(name) {
        const nameEQ = name + "=";
        const ca = document.cookie.split(';');
        for(let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0)==' ') c = c.substring(1,c.length);
            if (c.indexOf(nameEQ) == 0) return JSON.parse(c.substring(nameEQ.length,c.length));
        }
        return null;
    }
}


// ---------------------------------------------------------
// Notification Handlers
// ---------------------------------------------------------
/**
 * @typedef {Object} NotificationButton
 * @property {string} text - The label for the button.
 * @property {Function} [action] - The callback function to execute on click.
 * @property {boolean} [closeAfter=true] - Whether the notification should hide after clicking.
 */

/**
 * @typedef {Object} NotificationOptions
 * @property {string} [description] - Additional detailed text hidden behind a "More Info" toggle.
 * @property {NotificationButton[]} [buttons] - Array of custom button configurations.
 * @property {boolean} [blocking=false] - If true, locks scrolling and prevents interacting with the background.
 * @property {boolean} [overlay=false] - If true, displays a visual background cover behind the notification.
 */
export class NotificationManager {
    static boxId        = "message-box";
    static overlayId    = "message-overlay";
    static boxClassList = ["message-container"];
    static messageBox   = null;
    static overlayBox   = null;
    static timeoutId    = null;
    static options      = {};

    static DURATION_MIN = 10;

    // messages queue system
    static queue        = [];
    static isProcessing = false;

    /**
     * Self-Healing Initialization. Finds or creates the target DOM element.
     * @param {string} [elementId="message-box"] - The HTML ID of the message container.
     * @param {NotificationOptions} [options={}] - Default options to apply to the queue.
     */
    static init(elementId = this.boxId, options = {}) {
        this.boxId = elementId
        this.messageBox = document.getElementById(this.boxId);
        this.overlayBox = document.getElementById(this.overlayId);

        this.checkExistance();      // existance check, rebuilds element if missing
        this.setOptions(options);   // apply options as class default
    }


    // -- Class Utilities ---
    /**
     * Verifies DOM presences. Rebuilds if missing.
     */
    static checkExistance() {
        // check for overlay background
        if (!this.overlayBox) this.overlayBox = document.getElementById(this.overlayId);
        if (!this.overlayBox) {
            this.generateOverlay();
        }

        // check for message content box
        if (!this.messageBox) this.messageBox = document.getElementById(this.boxId);
        if (!this.messageBox) {
            console.warn(`[NotificationManager] Message box element missing. Rebuilding message box...`);
            this.generateNewBox();
        }
    }

    /**
     * Self-healing DOM injection for the background overlay.
     */
    static generateOverlay() {
        // remove old references
        this.removeOverlay();
        
        // define new overlay
        this.overlayBox = document.createElement("div");
        this.overlayBox.id = this.overlayId;
        this.overlayBox.className = "hidden";           // always initialise as hidden

        // append box to top of html body
        document.body.prepend(this.overlayBox);
    }

    /**
     * Self-healing DOM injection for the message box.
     */
    static generateNewBox() {
        // remove old references
        this.removeBox();

        // define new box
        this.messageBox = document.createElement("div");
        this.messageBox.id = this.boxId;

        // apply classes
        for (let cls of this.boxClassList) this.messageBox.classList.add(cls);
        this.messageBox.classList.add("hidden");        // always initialise as hidden

        // append box to top of html body
        document.body.prepend(this.messageBox);
    }

    /**
     * Clears internal HTML content.
     */
    static clearBox() {
        if (this.messageBox instanceof HTMLElement) {
            this.messageBox.innerHTML = "";
        }
    }

    /**
     * Completely removes the box from the DOM.
     */
    static removeOverlay() {
        if (this.overlayBox instanceof HTMLElement) {
            this.overlayBox.remove();
        }
        this.overlayBox = null;
    }

    /**
     * Completely removes the box from the DOM.
     */
    static removeBox() {
        if (this.messageBox instanceof HTMLElement) {
            this.messageBox.remove();
        }
        this.messageBox = null;
    }

    /**
     * Reads the CSS transition duration and adds a buffer to prevent JS race conditions.
     * @returns {number} The transition time in milliseconds.
     */
    static getTransitionTime() {
        const rootStyles    = getComputedStyle(document.documentElement);
        const timeStr       = rootStyles.getPropertyValue('--notify-transition-speed').trim() || '300ms';
        
        let time = 300;
        if (timeStr.endsWith('ms')) {
            time = parseInt(timeStr);
        } else if (timeStr.endsWith('s')) {
            time = parseFloat(timeStr) * 1000;
        }
        
        return time + 20;   // 20ms safety buffer
    }

    // --- Validation Controls ---
    /**
     * Strictly validates an array of queue items, stripping invalid objects safely.
     * @param {Array} queue - The array of tasks to validate.
     * @returns {Array} A clean, validated array of tasks.
     */
    static validateQueueArray(queue) {
        // validate queue type
        if (!Array.isArray(queue)) {
            console.warn("[NotificationManager] Invalid queue format, must be an array.");
            return [];
        }

        // filter invalid items
        const validQueue = queue.filter(item => {
            if (typeof item !== 'object' || Array.isArray(item) || item === null) {
                console.warn("[NotificationManager] Invalid queue item format. Must be an object. Dropping item.");
                return false;
            }

            if (!item.message || typeof item.message !== 'string' || item.message.trim() === "") {
                console.warn("[NotificationManager] Queue item missing valid 'message' string. Dropping item.");
                return false;
            }

            if (typeof item.isError !== 'boolean') {
                // gracefully ignore missing attribute
                item.isError = false;
            }

            if (typeof item.duration !== 'number' || item.duration < DURATION_MIN) {
                // gracefully ignore missing attribute
                item.duration = 4000;
            }

            return true;
        });

        // validate individual options within valid items
        validQueue.forEach(item => {
            if (item.options) {
                const validOptions = this.validateOptions(item.options);
                if (!validOptions || Object.keys(validOptions).length === 0) {
                    delete item.options;
                } else {
                    item.options = validOptions;
                }
            }
        });

        return validQueue;
    }

    /**
     * Validate passed options object and items.
     * @param {NotificationOptions} options 
     * @returns {NotificationOptions} A sanitized options object.
     */
    static validateOptions(options) {
        // validate options format and type
        if (typeof options !== 'object' || Array.isArray(options) || options === null) {
            console.warn("[NotificationManager] Invalid options format. Must be a valid object.");
            return {};
        }

        let sanitizedOpts = { ...options };

        if (!!sanitizedOpts.buttons) {
            let isValid = true;

            // button options must be an array
            if (!Array.isArray(sanitizedOpts.buttons)) {
                console.warn("[NotificationManager] Invalid options format. 'buttons' must be an array. Ignoring custom buttons.");
                isValid = false;

            } else if (sanitizedOpts.buttons.length === 0) {
                console.warn("[NotificationManager] Invalid array, 'buttons' array provided but is empty. Ignoring custom buttons.");
                isValid = false;
                
            } else {
                // every item in the array MUST be an object and MUST have a 'text' property
                const allButtonsValid = sanitizedOpts.buttons.every(btn => typeof btn === 'object' && btn !== null && !Array.isArray(btn) && btn.text && btn.closeAfter);
                
                if (!allButtonsValid) {
                    console.warn("[NotificationManager] Invalid button configuration. Each button must be an object containing a 'text' and 'closeAfter' property. Ignoring custom buttons.");
                    isValid = false;
                }
            }

            if (!isValid) delete sanitizedOpts.buttons;     // strip invalid buttons config
        }

        // validate boolean options for layout/blocking
        if (sanitizedOpts.blocking && typeof sanitizedOpts.blocking !== 'boolean') {
            sanitizedOpts.blocking = false;
        }
        if (sanitizedOpts.overlay && typeof sanitizedOpts.overlay !== 'boolean') {
            sanitizedOpts.overlay = false;
        }

        return sanitizedOpts;
    }

    /**
     * Safely merges global class options with task-specific overrides.
     * @param {NotificationOptions} taskOptions 
     * @returns {NotificationOptions}
     */
    static mergeOptions(taskOptions) {
        const globalOpts = this.getOptions();
        const localOpts = taskOptions || {};
        
        const deepMerge = (target, source) => {
            for (const key in source) {
                // check if both are objects (and not null/arrays) to recurse
                if (source[key] instanceof Object && !Array.isArray(source[key]) && key in target) {
                    Object.assign(source[key], deepMerge(target[key], source[key]));
                }
            }
            return { ...target, ...source };
        };

        return deepMerge(globalOpts, localOpts);
    }


    // --- Options Manager ---
    /**
     * Retrieves the current class-level default options.
     * @returns {NotificationOptions}
     */
    static getOptions() {
        return this.options;
    }

    /**
     * Sets class-level default options.
     * @param {NotificationOptions} options
     */
    static setOptions(options) {
        options = this.validateOptions(options);

        if (!options) return;

        // update 
        this.options = options;
    }

    /**
     * Clears all class-level options back to an empty object.
     */
    static clearOptions() {
        this.options = {};
        console.log(`[NotificationManager] Message box options list cleared.`);
    }
    

    // --- Display & Queue Controls ---
    /**
     * Displays a non-blocking UI notification.
     * @param {string} message - The text to display.
     * @param {boolean} [isError=false] - If true, styles the box with error colors.
     * @param {number} [duration=4000] - Milliseconds before the box auto-hides.
     * @param {NotificationOptions} [options={}] - Overrides for this specific task.
     */
    static show(message, isError = false, duration = 4000, options = {}) {
        if (!message || typeof message !== 'string' || message.trim() === "") {
            console.error(`[NotificationManager] Empty message passed. Skipping message box display.`)
            return;
        }

        // 
        const setOptions = this.validateOptions(options);

        // push to queue and process
        this.queue.push({ message, isError, duration, options: setOptions });
        this.processQueue();
    }

    /**
     * Ingests an array of message configurations into the queue.
     * @param {Array<Object>} queue - Array of tasks.
     * @param {NotificationOptions} [options={}] - Applies default options to the whole batch.
     */
    static showQueue(queue, options = {}) {
        // validate queue is valid array of objects '[{ message, isError, duration, options (override) }]'
        queue = this.validateQueueArray(queue);

        if (!queue || queue.length === 0) return;

        this.setOptions(options);

        // push to queue and process
        queue.forEach(msg => this.queue.push(msg))
        this.processQueue();
    }

    /**
     * Evaluates the queue and prevents overlapping renders.
     */
    static processQueue() {
        if (this.isProcessing) return;      // prevent concurrent rendering

        if (this.queue.length === 0) {
            this.clearOptions();            // clean up class defaults when queue finishes
            return;
        }
        
        this.isProcessing = true;
        this.checkExistance();              // ensure DOM element exists

        const currentTask = this.queue.shift();
        this.renderMessage(currentTask);
    }


    // --- Rendering Orchestration ---
    /**
     * Orchestrates DOM manipulation for a single notification task.
     * @param {Object} task - The validated queue item.
     */
    static renderMessage(task) {
        let { message, isError, duration, options } = task;

        // resolve options
        let finalOptions = this.mergeOptions(options);

        // prep DOM
        this.clearBox();
        this.applyStyles(isError, finalOptions);

        // build content
        this.buildTextNode(message);


        let descDiv = null;
        if (finalOptions.description) {
            descDiv = this.buildDescriptionNode(finalOptions.description);
        }

        if (finalOptions.description || finalOptions.buttons) {
            this.buildButtons(finalOptions, descDiv);
        }

        // reveal
        this.messageBox.classList.remove("hidden");

        // clear previous timer
        if (this.timeoutId) clearTimeout(this.timeoutId);

        // set new timer and ensure duration is above minimum
        if (duration <= DURATION_MIN) {
            duration = DURATION_MIN;
        }
        this.timeoutId = setTimeout(() => this.hide(), duration);
    }


    // --- DOM Construction Helpers ---
    /**
     * Applies colors, layout boundaries, and overlay/blocking states.
     * @param {boolean} isError 
     * @param {NotificationOptions} options 
     */
    static applyStyles(isError, options) {
        this.messageBox.style.backgroundColor = isError ? "var(--error-bg)" : "var(--success-bg)";
        this.messageBox.style.color = isError ? "var(--error-color)" : "var(--success-text)";

        // handle blocker/overlay
        if (options.blocking) {
            document.body.style.overflow = "hidden";        // prevent page scrolling

            const bodyContent = document.querySelectorAll(`body > :not(#${this.boxId}):not(script)`);
            bodyContent.forEach(el => el.inert = true);     // prevent any interaction
        }

        if (options.overlay || options.blocking) {
            this.overlayBox.classList.remove("hidden");     // reveal overlay

            const bodyContent = document.querySelectorAll(`body > :not(#${this.boxId}):not(script)`);
            bodyContent.forEach(el => el.inert = true);     // prevent any interaction
        }
    }

    /**
     * Appends the core message text to the box.
     * @param {string} message 
     */
    static buildTextNode(message) {
        const msgDiv = document.createElement("div");
        msgDiv.style.fontWeight = "bold";
        msgDiv.textContent = message;
        this.messageBox.appendChild(msgDiv);
    }

    /**
     * Appends hidden description text for the toggle button.
     * @param {string} descText 
     * @returns {HTMLElement}
     */
    static buildDescriptionNode(descText) {
        const descDiv = document.createElement("div");
        descDiv.style.maxHeight = "0px";
        descDiv.style.opacity = "0";
        descDiv.style.overflow = "hidden";
        descDiv.style.transition = `all var(--notify-transition-speed, 0.3s) ease-in-out`;
        descDiv.style.fontSize = "0.9rem";
        descDiv.textContent = descText;
        this.messageBox.appendChild(descDiv);
        return descDiv;
    }

    /**
     * Orchestrates button creation and injection.
     * @param {NotificationOptions} options 
     * @param {HTMLElement} descDiv 
     */
    static buildButtons(options, descDiv) {
        const btnContainer = document.createElement("div");
        btnContainer.style.display = "flex";
        btnContainer.style.gap = "10px";
        btnContainer.style.marginTop = "12px";
        this.messageBox.appendChild(btnContainer);

        // auto-add toggle info button if description exists
        if (descDiv) {
            const infoBtn = document.createElement("button");
            infoBtn.textContent = "More Info";
            infoBtn.className = "btn-secondary text-sm";
            infoBtn.onclick = () => this.toggleDisplayInfo(descDiv);
            btnContainer.appendChild(infoBtn);
        }

        // add user-defined custom buttons
        if (options.buttons) {
            options.buttons.forEach(btnConfig => {
                const btn = document.createElement("button");
                btn.textContent = btnConfig.text;
                btn.className = "btn-primary text-sm";
                btn.onclick = () => {
                    if (btnConfig.action) btnConfig.action();
                    if (btnConfig.closeAfter !== false) this.hide(); 
                };
                btnContainer.appendChild(btn);
            });
        }

        // always include default manual close button
        const exitBtn = document.createElement("button");
        exitBtn.textContent = "Close";
        exitBtn.className = "btn-secondary text-sm";
        exitBtn.onclick = () => this.hide();
        btnContainer.appendChild(exitBtn);
    }


    // --- Interaction & Lifecyle Helpers ---
    /**
     * Hides notification, clears block/overlay, and triggers next queue item.
     */
    static hide() {
        if (this.timeoutId) clearTimeout(this.timeoutId);

        // remove page blocking/overlay
        document.body.style.overflow = "";
        if (this.overlayBox) this.overlayBox.classList.add("hidden");

        const bodyContent = document.querySelectorAll(`body > *`);
            bodyContent.forEach(el => el.removeAttribute('inert'));


        if (this.messageBox) {
            this.messageBox.classList.add("hidden");
            
            // allow CSS transition before wiping HTML
            setTimeout(() => {
                this.clearBox();
                this.isProcessing = false;
                this.processQueue();
            }, this.getTransitionTime());
        } else {
            this.isProcessing = false;
            this.processQueue();
        }
    }

    /**
     * Toggles smooth expanding/collapsing of the description text box.
     * @param {HTMLElement} descDiv 
     */
    static toggleDisplayInfo(descDiv) {
        if (descDiv.style.maxHeight === "0px" || !descDiv.style.maxHeight) {
            descDiv.style.maxHeight = "150px"; 
            descDiv.style.opacity = "1";
            descDiv.style.marginTop = "8px";
        } else {
            descDiv.style.maxHeight = "0px";
            descDiv.style.opacity = "0";
            descDiv.style.marginTop = "0px";
        }
    }
}

// ---------------------------------------------------------
// DOM Utility Methods
// ---------------------------------------------------------
export class DOMUtils {
    // --- FUTURE UTILS HERE ---

    /**
     * Iterates over a configuration dictionary of selector strings and maps them to active DOM elements.
     * @param {Object} selectors - Dictionary of key: "html-id" pairs.
     * @returns {Object} Dictionary of key: HTMLElement pairs.
     */
    static mapElements(selectors) {
        return Object.entries(selectors).reduce((acc, [key, id]) => {
            acc[key] = document.getElementById(id);
            return acc;
        }, {});
    }
}


// ---------------------------------------------------------
// UI Component Managers
// ---------------------------------------------------------
export class DatalistManager {
    static availableModels = [];

    /**
     * Fetches the model registry from the backend to populate dropdowns.
     * @param {Object} API - The imported API module to make the fetch request.
     */
    static async initialize(API) {
        try {
            const data = await API.getModels();
            this.availableModels = data.models;
        } catch (error) {
            console.error("Failed to load models list:", error);
        }
    }

    /**
     * Binds the custom dropdown logic to a specific input and list element.
     * @param {string} inputId - The ID of the text input.
     * @param {string} listId - The ID of the hidden unordered list.
     */
    static setup(inputId, listId) {
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
}