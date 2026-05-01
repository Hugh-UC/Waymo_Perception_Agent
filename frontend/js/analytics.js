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

        this.magmaPalette = this.getPalette('magma', 11);
        this.coolwarmPalette = this.getPalette('cw', 11);
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

    // mathematical interpolator for continuous gradients between two hex codes
    interpolateColor(color1, color2, factor) {
        let result = "#";
        for (let i = 0; i < 3; i++) {
            let c1 = parseInt(color1.substring(1 + i * 2, 3 + i * 2), 16);
            let c2 = parseInt(color2.substring(1 + i * 2, 3 + i * 2), 16);
            let c = Math.round(c1 + factor * (c2 - c1));
            result += c.toString(16).padStart(2, '0');
        }
        return result;
    }

    // maps an index (0.0 to 1.0) perfectly across an array of N colors
    getColorFromPalette(paletteArray, normalizedValue) {
        let exactIndex = normalizedValue * (paletteArray.length - 1);
        let idx1 = Math.floor(exactIndex);
        let idx2 = Math.ceil(exactIndex);
        let factor = exactIndex - idx1;
        return this.interpolateColor(paletteArray[idx1], paletteArray[idx2], factor);
    }

    render(config, dataPayload) {
        if (!this.ctx) return;
        this.clear();
        
        // map of chart types
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

            // configure datapoints tooltip
            options.plugins.tooltip = {
                callbacks: {
                    label: function(context) {
                        // get original label
                        let originalLabel = context.dataset.label;
                        
                        // remove text after parenthesis
                        let cleanLabel = originalLabel.split(' (')[0];
                        
                        // return clean label
                        return `${cleanLabel}: ${context.raw.toFixed(2)}`;
                    }
                }
            };
        }
        else if (config.type === 'frequency_bar') {
            options.indexAxis = 'y'; 
            options.plugins.legend.display = false;                 // hide legend
            options.plugins.datalabels = { display: false };        // hide labels
            options.scales.y.grid = { display: false };             // hide grid lines
        }
        else if(config.type === 'avg_metric_bar') {
            options.indexAxis = 'y'; 
            options.plugins.legend.display = false;                 // hide legend
            options.plugins.datalabels = { display: false };        // hide labels
            options.scales.y.grid = { display: false };             // hide grid lines

            options.scales.y.ticks = {
                autoSkip: false,
                color: this.textColor,
                font: { size: 9 }                                  // slightly smaller font
            };

            // destinct verticle line at 0
            options.scales.x.grid = {
                color: (context) => context.tick.value === 0 ? '#888888' : 'transparent',
                lineWidth: (context) => context.tick.value === 0 ? 1 : 0
            };
        }
        else if (config.type === 'bubble_scatter') {
            // force explicitly linear axes for bubbles
            // x-axis
            options.scales.x.type = 'category';
            options.scales.x.labels = ['Pessimistic', 'Neutral', 'Optimistic', 'Inspired'];
            options.scales.x.title = { display: true, text: config.x_label, color: this.textColor };
            options.scales.x.offset = true;
            // y-axis
            options.scales.y.type = 'linear';
            options.scales.y.title = { display: true, text: config.y_label, color: this.textColor };
            options.scales.y.suggestedMin = 0; 
            options.scales.y.suggestedMax = 10;
            options.scales.y.offset = true;
            
            // hide labels
            options.plugins.datalabels = { display: false };

            // configure datapoints tooltip
            options.plugins.tooltip = {
                callbacks: {
                    // customize body text of the hover tooltip
                    label: function(context) {
                        // reverse engineer relatability score from the radius (r)
                        let relScore = ((context.raw.r - 4) / 16).toFixed(2);

                        let safetyScore = context.raw.y;
                        
                        // returning array automatically creates beautifully spaced multiple lines!
                        return [
                            `${context.dataset.label}:`,
                            `| relatability - ${relScore}`,
                            `| perception - ${safetyScore}`
                        ];
                    }
                }
            };
        }

        // --- Palette Application ---
        dataPayload.datasets.forEach((dataset, index) => {
            if (config.type === 'frequency_bar') {
                // map magma gradient
                dataset.backgroundColor = dataset.data.map((_, i) => this.magmaPalette[i % this.magmaPalette.length]);
                dataset.borderWidth = 0;
                dataset.barPercentage = 0.95;
                dataset.categoryPercentage = 1.0;
            } 
            else if (config.type === 'avg_metric_bar') {
                // continuous gradient mapping
                dataset.backgroundColor = dataset.data.map((_, i) => {
                    let norm = dataset.data.length > 1 ? i / (dataset.data.length - 1) : 0;
                    return this.getColorFromPalette(this.coolwarmPalette, norm);
                });
                dataset.borderWidth = 0;
                // thicken bars (matplotlib style)
                dataset.barPercentage = 0.95;
                dataset.categoryPercentage = 1.0;;
            }
            else if (config.type === 'dual_axis_line') {
                dataset.backgroundColor = 'transparent';                    // remove fill
                dataset.borderColor = this.genericPalette[index];
                dataset.pointBackgroundColor = this.genericPalette[index];
                dataset.pointStyle = index === 0 ? 'circle' : 'rect';       // match python shapes
                dataset.pointRadius = 5;
                dataset.pointHoverRadius = 8;
                dataset.borderWidth = 3;
                dataset.tension = 0.3;                                      // curve the lines
            } 
            else if (config.type === 'bubble_scatter') {
                // assign colours
                let color = dataset.label === 'News' ? this.genericPalette[2] : this.genericPalette[3];
                dataset.backgroundColor = color + '40';                     // hex + '40' = 25% opacity
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