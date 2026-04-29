/**
 * File: analytics.js
 * Title: Data Visualisation & Dashboard Controller
 * Description: Manages Chart.js rendering, data filtering, and AI Narrative UI.
 */

class ChartRenderer {
    constructor(canvasId) {
        this.canvasId = canvasId;
        this.chartInstance = null;
        
        const canvas = document.getElementById(this.canvasId);
        if (!canvas) return; // Prevent crashes if canvas isn't on page
        this.ctx = canvas.getContext('2d');
        
        // Use CSS variables for seamless light/dark mode transitions
        const style = getComputedStyle(document.body);
        this.textColor = style.getPropertyValue('--text-primary').trim() || '#cbd5e1';
        this.gridColor = style.getPropertyValue('--border-color').trim() || '#334155';
        this.primaryColor = '#3b82f6';
        this.secondaryColor = '#a855f7';
    }

    clear() {
        if (this.chartInstance) this.chartInstance.destroy();
    }

    render(config, dataPayload) {
        if (!this.ctx) return;
        this.clear();
        
        const typeMap = {
            'frequency_bar': 'bar',
            'avg_metric_bar': 'bar',
            'dual_axis_line': 'line',
            'bubble_scatter': 'bubble'
        };

        const chartType = typeMap[config.type] || 'bar';
        
        let options = {
            responsive: true,
            maintainAspectRatio: false,
            color: this.textColor,
            plugins: {
                title: { display: true, text: config.title, color: this.textColor, font: { size: 16 } },
                legend: { labels: { color: this.textColor } }
            },
            scales: {
                x: { grid: { color: this.gridColor }, ticks: { color: this.textColor } },
                y: { grid: { color: this.gridColor }, ticks: { color: this.textColor } }
            }
        };

        if (config.type === 'dual_axis_line') {
            options.scales.y = { type: 'linear', position: 'left', title: { display: true, text: config.y_label, color: this.textColor } };
            options.scales.y1 = { type: 'linear', position: 'right', title: { display: true, text: config.y2_label, color: this.textColor }, grid: { drawOnChartArea: false } };
        } else if (config.type === 'frequency_bar' || config.type === 'avg_metric_bar') {
            options.indexAxis = 'y'; 
        }

        // expanded color palette for bubble hues
        const palette = ['#3b82f6', '#a855f7', '#10b981', '#f59e0b', '#ef4444', '#06b6d4'];

        dataPayload.datasets.forEach((dataset, index) => {
            const hexColor = palette[index % palette.length];
            
            if (config.type === 'bubble_scatter') {
                // add 50% opacity (80 in hex) for overlapping bubbles
                dataset.backgroundColor = hexColor + '80';
            } else if (config.type === 'dual_axis_line') {
                // prevent line charts from filling area underneath
                dataset.backgroundColor = 'transparent';
            } else {
                dataset.backgroundColor = hexColor;
            }
            
            dataset.borderColor = hexColor;
            dataset.borderWidth = 2;
        });

        this.chartInstance = new Chart(this.ctx, {
            type: chartType,
            data: dataPayload,
            options: options
        });
    }
}

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