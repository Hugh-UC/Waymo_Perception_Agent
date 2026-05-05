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
export class NotificationManager {
    static statusBox = null;
    static timeoutId = null;

    /**
     * Finds and caches the target DOM element for notifications.
     * @param {string} elementId - The HTML ID of the status container.
     */
    static init(elementId = "save-status") {
        this.statusBox = document.getElementById(elementId);
    }

    /**
     * Displays a non-blocking UI notification.
     * @param {string} message - The text to display.
     * @param {boolean} [isError=false] - If true, styles the box with error colors.
     * @param {number} [duration=4000] - Milliseconds before the box auto-hides.
     */
    static show(message, isError = false, duration = 4000) {
        if (!this.statusBox) this.init();
        if (!this.statusBox) {
            console.warn(`[System Error] Failed to display message to user: '${message}'. Status box element missing.`);
            return;
        }

        // Clear existing timeout if a new message comes in rapidly
        if (this.timeoutId) clearTimeout(this.timeoutId);
        
        this.statusBox.textContent = message;
        this.statusBox.style.backgroundColor = isError ? "var(--error-bg)" : "var(--success-bg)";
        this.statusBox.style.color = isError ? "var(--error-color)" : "var(--success-text)";
        this.statusBox.classList.remove("hidden");
        
        this.timeoutId = setTimeout(() => {
            if(this.statusBox) this.statusBox.classList.add("hidden");
        }, duration);
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