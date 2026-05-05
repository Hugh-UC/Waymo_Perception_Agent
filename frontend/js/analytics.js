/**
 * File: analytics.js
 * Title: Data Visualisation & Dashboard Controller
 * Description: Manages data fetching, DOM interactions, and AI Narrative UI.
 */

// import chart rendering class
import { ChartRenderer } from './tools/ChartRenderer.js';


class DashboardController {
    constructor() {
        this.activeCharts = ['trend_analysis', 'city_risk', 'friction_points', 'media_battlefield'];
        this.renderers = {};
    }

    async init() {
        this.setupNavigation();
        this.setupEventListeners();
        await this.loadAllCharts();
    }

    setupNavigation() {
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
    }

    setupEventListeners() {
        const timeFilter = document.getElementById("graph-time-filter");
        if (timeFilter) {
            timeFilter.addEventListener("change", () => this.loadAllCharts());
        }
    }

    async loadAllCharts() {
        const timeFilter = document.getElementById("graph-time-filter");
        const daysBack = timeFilter ? timeFilter.value : 60;
        
        for (const chartId of this.activeCharts) {
            try {
                const response = await fetch(`/api/analytics/chart/${chartId}?days_back=${daysBack}`);
                const result = await response.json();
                
                if (result.status === 'success') {
                    if (!this.renderers[chartId]) {
                        this.renderers[chartId] = new ChartRenderer(`${chartId}-canvas`);
                    }
                    this.renderers[chartId].render(result.config, result.data);
                }
            } catch (error) {
                console.error(`Failed to load chart ${chartId}:`, error);
            }
        }
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const dashboard = new DashboardController();
    dashboard.init();
});