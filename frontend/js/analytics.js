/**
 * File: analytics.js
 * Title: Data Visualisation & Dashboard Controller
 * Description: Manages Chart.js rendering, data filtering, and AI Narrative UI.
 */

// register official plugin for bubble annotations
Chart.register(ChartDataLabels);

class ChartRenderer {
    constructor(canvasId) {
        this.canvasId = canvasId;
        this.chartInstance = null;
        
        const canvas = document.getElementById(this.canvasId);
        if (!canvas) return;        // prevent crashes if canvas isn't on page
        this.ctx = canvas.getContext('2d');
        
        // use CSS variables for seamless light/dark mode transitions
        const style = getComputedStyle(document.body);
        this.textColor = style.getPropertyValue('--text-primary').trim() || '#cbd5e1';
        this.gridColor = style.getPropertyValue('--border-color').trim() || '#334155';

        // helper to pull gradients
        this.getPalette = (prefix, count) => {
            let p = [];
            for(let i=1; i<=count; i++) p.push(style.getPropertyValue(`--${prefix}-${i}`).trim());
            return p;
        };

        this.magmaPalette = this.getPalette('magma', 8);
        this.coolwarmPalette = this.getPalette('cw', 8);
        this.genericPalette = [
            style.getPropertyValue('--chart-color-1').trim(),
            style.getPropertyValue('--chart-color-2').trim(),
            style.getPropertyValue('--chart-color-3').trim(),
            style.getPropertyValue('--chart-color-4').trim()
        ];
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
        
        // --- Structural Overrides ---
        if (config.type === 'dual_axis_line') {
            options.scales.y = { type: 'linear', position: 'left', title: { display: true, text: config.y_label, color: this.textColor } };
            options.scales.y1 = { type: 'linear', position: 'right', title: { display: true, text: config.y2_label, color: this.textColor }, grid: { drawOnChartArea: false } };
            options.plugins.datalabels = { display: false };        // hide labels
        } 
        else if (config.type === 'frequency_bar' || config.type === 'avg_metric_bar') {
            options.indexAxis = 'y'; 
            options.plugins.legend.display = false; 
            options.plugins.datalabels = { display: false };        // hide labels
        }
        else if (config.type === 'bubble_scatter') {
            // force explicitly linear axes for bubbles
            options.scales.x.type = 'linear';
            options.scales.x.title = { display: true, text: config.x_label, color: this.textColor };
            options.scales.y.type = 'linear';
            options.scales.y.title = { display: true, text: config.y_label, color: this.textColor };
            
            // configure text for bubbles
            options.plugins.datalabels = {
                color: '#ffffff',
                font: { size: 10, weight: 'bold' },
                align: 'top',
                offset: 5,
                formatter: function(value, context) {
                    // reverse engineer relatability score from radius
                    let relScore = ((value.r - 5) / 25).toFixed(1);
                    return `${context.dataset.label}\n(Rel: ${relScore})`;
                }
            };
        }

        // --- Palette Application ---
        dataPayload.datasets.forEach((dataset, index) => {
            if (config.type === 'frequency_bar') {
                // map magma gradient
                dataset.backgroundColor = dataset.data.map((_, i) => this.magmaPalette[i % this.magmaPalette.length]);
                dataset.borderWidth = 0;
            } 
            else if (config.type === 'avg_metric_bar') {
                // map coolwarm gradient
                dataset.backgroundColor = dataset.data.map(val => {
                    if (val > 0.7) return this.coolwarmPalette[0];
                    if (val > 0.4) return this.coolwarmPalette[1];
                    if (val > 0.1) return this.coolwarmPalette[2];
                    if (val > -0.1) return this.coolwarmPalette[3];
                    if (val > -0.4) return this.coolwarmPalette[4];
                    if (val > -0.7) return this.coolwarmPalette[5];
                    return this.coolwarmPalette[7];
                });
                dataset.borderWidth = 0;
            }
            else if (config.type === 'dual_axis_line') {
                dataset.backgroundColor = 'transparent';        // remove fill
                dataset.borderColor = this.genericPalette[index];
                dataset.pointBackgroundColor = this.genericPalette[index];
                dataset.pointStyle = index === 0 ? 'circle' : 'rect';       // match python shapes
                dataset.pointRadius = 5;
                dataset.pointHoverRadius = 8;
                dataset.borderWidth = 3;
                dataset.tension = 0.3;      // curve the lines
            } 
            else if (config.type === 'bubble_scatter') {
                // assign colours
                let color = dataset.label === 'News' ? this.genericPalette[2] : this.genericPalette[3];
                dataset.backgroundColor = color + '80';     // hex + '80' = 50% opacity
                dataset.borderColor = color;
                dataset.borderWidth = 2;
            }
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