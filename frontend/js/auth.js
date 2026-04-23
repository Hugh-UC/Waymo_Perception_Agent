/**
 * File: auth.js
 * Title: Authentication & State Controller
 * Description: Handles Auth UI, masked key logic, password validation, 
 * and a persistent multi-step wizard.
 * Author: Hugh Brennan
 * Date: 2026-04-22
 * Version: 0.4
 */

const AuthManager = {
    // ---------------------------------------------------------
    // Session & Cookie Management
    // ---------------------------------------------------------
    setSession(username) {
        const d = new Date();
        d.setTime(d.getTime() + (24 * 60 * 60 * 1000));
        document.cookie = `waymo_session=${username};expires=${d.toUTCString()};path=/`;
    },
    
    getSession() {
        const match = document.cookie.match(new RegExp('(^| )waymo_session=([^;]+)'));
        return match ? match[2] : null;
    },
    
    clearSession() { 
        document.cookie = "waymo_session=; Max-Age=-99999999; path=/;"; 
    },
    
    isPasswordSafe(pwd) {
        if (pwd.length < 8) return false;
        return !(/[&|;$><`\\!]/.test(pwd));
    },


    // ---------------------------------------------------------
    // Setup Wizard Smart State Management
    // ---------------------------------------------------------
    wizardFallbackModels: [],
    
    /**
     * Transitions the UI to a specific wizard step and updates the progress bar.
     * @param {number} stepNumber - The target step (0, 1, 2, or 3).
     */
    goToStep(stepNumber) {
        document.querySelectorAll('.wizard-step').forEach(el => el.classList.add('hidden'));
        
        const targetStep = document.getElementById(`step-${stepNumber}`);
        if (targetStep) targetStep.classList.remove('hidden');
        
        // Update Progress Bar (4 steps total: 0 = 0%, 1 = 33%, 2 = 66%, 3 = 100%)
        const progressFill = document.getElementById('progress-fill');
        if (progressFill) {
            const percentage = (stepNumber / 3) * 100; 
            progressFill.style.width = `${percentage}%`;
        }
        
        localStorage.setItem("waymo_wizard_step", stepNumber.toString());
    },

    /**
     * Prefills an input with a masked string (e.g. **********a48f) and disables it.
     * Activates the "Clear key" button to allow users to overwrite it.
     */
    setupMaskedInput(inputId, wrapperId, btnId, maskedValue) {
        const input = document.getElementById(inputId);
        const wrapper = document.getElementById(wrapperId);
        const btn = document.getElementById(btnId);

        if (input && wrapper && btn && maskedValue) {
            input.value = maskedValue;
            input.disabled = true;
            input.dataset.isMasked = "true"; 
            wrapper.classList.remove("hidden");

            // Attach listener to clear and unlock the input
            btn.addEventListener("click", () => {
                input.value = "";
                input.disabled = false;
                input.dataset.isMasked = "false";
                wrapper.classList.add("hidden");
                input.focus();
            }, { once: true });
        }
    },

    /**
     * Renders the visual tags for fallback models in Step 2.
     */
    renderWizardFallbackTags() {
        const container = document.getElementById("setup-fallback-tags");
        if (!container) return;
        container.innerHTML = "";
        
        this.wizardFallbackModels.forEach((model, index) => {
            const tag = document.createElement("div");
            tag.className = "tag";
            tag.innerHTML = `${model} <button type="button" data-index="${index}">×</button>`;
            container.appendChild(tag);
        });

        container.querySelectorAll("button").forEach(btn => {
            btn.addEventListener("click", (e) => {
                this.wizardFallbackModels.splice(e.target.getAttribute("data-index"), 1);
                this.renderWizardFallbackTags();
            });
        });
    },
    
    /**
     * Parses the backend status to prefill parameters and route the user
     * to the exact step they need to complete.
     */
    initializeWizardState(status) {
        // 1. prefill ENV parameters if backend provides masked versions
        if (status.masked_gemini) {
            this.setupMaskedInput("setup-gemini", "clear-gemini-wrapper", "btn-clear-gemini", status.masked_gemini);
        }
        if (status.masked_news) {
            this.setupMaskedInput("setup-news", "clear-news-wrapper", "btn-clear-news", status.masked_news);
        }

        // 2. prefill YAML configurations
        if (status.config && status.config.agent) {
            const primaryInput = document.getElementById("setup-primary-model");
            if (primaryInput) primaryInput.value = status.config.agent.model_name || "";

            this.wizardFallbackModels = status.config.agent.fallback_model || [];
            this.renderWizardFallbackTags();
        }

        // 3. smart routing
        let targetStep = 1;
        const savedStep = parseInt(localStorage.getItem("waymo_wizard_step"));
        
        if (savedStep) {
            targetStep = savedStep;
        } else if (status.missing_env) {
            targetStep = 1;     // needs API Keys
        } else if (status.missing_config) {
            targetStep = 2;     // needs Model Configs
        } else if (status.missing_auth) {
            targetStep = 3;     // needs Admin Account
        }

        this.nextIncompleteStep = targetStep;

        // 4. update 'Step 0' UI buttons
        const btnStart = document.getElementById("btn-start-wizard");
        const btnContinue = document.getElementById("btn-continue-wizard");
        const btnRestart = document.getElementById("btn-restart-wizard");

        // toggle buttons based on step progress
        if (targetStep > 1) {
            if (btnStart) btnStart.classList.add("hidden");
            if (btnContinue) btnContinue.classList.remove("hidden");
            if (btnRestart) btnRestart.classList.remove("hidden");
        } else {
            if (btnStart) btnStart.classList.remove("hidden");
            if (btnContinue) btnContinue.classList.add("hidden");
            if (btnRestart) btnRestart.classList.add("hidden");
        }

        // 5. go to welcome screen
        this.goToStep(0);
    }
};

window.AuthManager = AuthManager;

// progress controller
document.addEventListener("DOMContentLoaded", () => {
    // get modal elements
    const wizardModal = document.getElementById("setup-wizard");
    const loginModal = document.getElementById("login-overlay");
    const appContainer = document.getElementById("app-container");

    // Step 0: Intro
    document.getElementById("btn-start-wizard")?.addEventListener("click", () => {
        if (AuthManager.nextIncompleteStep <= 1) {AuthManager.goToStep(1);}
    });

    document.getElementById("btn-continue-wizard")?.addEventListener("click", () => {
        if (AuthManager.nextIncompleteStep > 1) {AuthManager.goToStep(AuthManager.nextIncompleteStep);}
    });

    document.getElementById("btn-restart-wizard")?.addEventListener("click", () => {
        if (AuthManager.nextIncompleteStep > 1) {
            localStorage.removeItem("waymo_wizard_step"); // clear saved progress
            AuthManager.nextIncompleteStep = 1;           // reset internal state 
            AuthManager.goToStep(1);
        }
    });


    // Step 1: save APIs
    document.getElementById("form-step-1")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const errBox = document.getElementById("setup-error");
        errBox.classList.add("hidden");

        const geminiInput = document.getElementById("setup-gemini");
        const newsInput = document.getElementById("setup-news");
        const payload = {};

        // include keys in payload,
        // if they have been actively altered or are brand new
        if (geminiInput.dataset.isMasked !== "true") {
            payload.gemini_key = geminiInput.value.trim();
        }
        if (newsInput.dataset.isMasked !== "true") {
            payload.news_key = newsInput.value.trim();
        }

        try {
            // fire the API request, if there is new unmasked data
            if (Object.keys(payload).length > 0) {
                await window.API.setupKeys(payload);
            }
            // move to next step
            AuthManager.goToStep(2);
        } catch (error) {
            errBox.textContent = error.detail ? `Server Error: ${error.detail}` : "Failed to save API keys.";
            errBox.classList.remove("hidden");
        }
    });


    // Step 2: agent intelligence models
    document.getElementById("btn-add-setup-fallback")?.addEventListener("click", () => {
        const input = document.getElementById("setup-new-fallback");
        const errBox = document.getElementById("setup-fallback-error");
        errBox.classList.add("hidden");
        
        const val = input.value.trim();
        if (!val) return;
        
        if (AuthManager.wizardFallbackModels.includes(val)) {
            errBox.textContent = "Model is already in the fallback list.";
            errBox.classList.remove("hidden");
            return;
        }

        AuthManager.wizardFallbackModels.push(val);
        input.value = "";
        AuthManager.renderWizardFallbackTags();
    });

    document.getElementById("form-step-2")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const errBox = document.getElementById("setup-model-error");
        errBox.classList.add("hidden");

        try {
            const config = await window.API.getConfig();
            config.agent.model_name = document.getElementById("setup-primary-model").value.trim();
            config.agent.fallback_model = AuthManager.wizardFallbackModels;
            
            await window.API.updateConfig({ scraper: config.scraper, agent: config.agent });
            AuthManager.goToStep(3);
        } catch(error) {
            errBox.textContent = "Failed to update params.yaml.";
            errBox.classList.remove("hidden");
        }
    });


    // Step 3: register local admin
    document.getElementById("form-step-3")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const errBox = document.getElementById("register-error");
        errBox.classList.add("hidden");

        const user = document.getElementById("new-user").value.trim();
        const pass = document.getElementById("new-pass").value;

        if (!AuthManager.isPasswordSafe(pass)) {
            errBox.textContent = "Password must be 8+ characters without shell symbols (&, |, ;, $).";
            errBox.classList.remove("hidden");
            return;
        }

        try {
            await window.API.registerUser({ username: user, password: pass });
            
            localStorage.removeItem("waymo_wizard_step"); 
            AuthManager.setSession(user);
            
            wizardModal.classList.add("hidden");
            appContainer.classList.remove("hidden");
            document.getElementById("btn-logout")?.classList.remove("hidden");
            
        } catch (error) {
            errBox.textContent = error.detail ? `Registration failed: ${error.detail}` : "Network Error.";
            errBox.classList.remove("hidden");
        }
    });


    // login overlay
    document.getElementById("login-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const errBox = document.getElementById("login-error");
        errBox.classList.add("hidden");

        const user = document.getElementById("login-user").value.trim();
        const pass = document.getElementById("login-pass").value;

        try {
            const data = await window.API.loginUser({ username: user, password: pass });
            if (data.authenticated) {
                AuthManager.setSession(user);
                loginModal.classList.add("hidden");
                appContainer.classList.remove("hidden");
                document.getElementById("btn-logout")?.classList.remove("hidden");
            } else {
                errBox.textContent = "Incorrect Username or Password.";
                errBox.classList.remove("hidden");
            }
        } catch (error) {
            errBox.textContent = "Network Error communicating with server.";
            errBox.classList.remove("hidden");
        }
    });


    // logout
    document.getElementById("btn-logout")?.addEventListener("click", () => {
        AuthManager.clearSession();
        window.location.reload(); 
    });


    // boot
    if (window.BootManager) window.BootManager.initialize();
});