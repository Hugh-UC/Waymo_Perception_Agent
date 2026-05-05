/**
 * File: ChartRenderer.js
 * Title: 
 * Description: A dynamic, JSON-driven wrapper for Chart.js
 */

// register official plugin for bubble annotations
Chart.register(ChartDataLabels);

export class ChartRenderer {
    constructor(canvasId) {
        this.canvasId = canvasId;
        this.chartInstance = null;
        
        const canvas = document.getElementById(this.canvasId);
        if (!canvas) return;        // prevent crashes if canvas isn't on page
        this.ctx = canvas.getContext('2d');
        
        // use CSS variables for seamless light/dark mode transitions
        const style = getComputedStyle(document.body);
        this.textColor = style.getPropertyValue('--text-primary').trim() || '#cbd5e1';
        this.titleSize = style.getPropertyValue('--chart-title-l').trim().replace('px', '') || '16';
        this.tickSize = style.getPropertyValue('--chart-tick-m').trim().replace('px', '') || '11'; 
        this.gridColor = style.getPropertyValue('--border-color').trim() || '#334155';
        this.zeroLineColor = style.getPropertyValue('--chart-zeroline').trim() || '#9A9B9C';

        // helper to pull gradients
        this.getPalette = (prefix, count) => {
            let p = [];
            for(let i=1; i<=count; i++) p.push(style.getPropertyValue(`--${prefix}-${i}`).trim());
            return p;
        };

        // define colour palettes
        this.palettes = {
            'magma': this.getPalette('magma', 11),
            'coolwarm': this.getPalette('cw', 11),
            'generic': [
                style.getPropertyValue('--chart-color-1').trim(),
                style.getPropertyValue('--chart-color-2').trim(),
                style.getPropertyValue('--chart-color-3').trim(),
                style.getPropertyValue('--chart-color-4').trim(),
                style.getPropertyValue('--chart-color-5').trim(),
                style.getPropertyValue('--chart-color-6').trim()
            ]
        };
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

    // --- Dynamic Base Configuration ---
    defaultOptionsConfig(config) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            color: this.textColor,
            indexAxis: 'x', 
            plugins: {
                title: { display: true, text: config.title, color: this.textColor, font: { size: this.titleSize } },
                legend: { labels: { color: this.textColor } },
                tooltip: { callbacks: {} }
            },
            scales: {
                x: { 
                    grid: { display: true, color: this.gridColor }, 
                    ticks: { color: this.textColor, font: { size: this.tickSize } }
                },
                y: { 
                    grid: { display: true, color: this.gridColor }, 
                    ticks: { color: this.textColor, autoSkip: false, font: { size: this.tickSize } }
                }
            }
        };
    }

    // --- Structural Overrides ---
    applyStructuralOverrides(options, pres, config, chartType) {
        // Core Layout
        if (pres.index_axis) options.indexAxis = pres.index_axis;

        // Plugin Toggles
        if (pres.show_legend !== undefined) options.plugins.legend.display = pres.show_legend;
        if (pres.hide_datalabels !== undefined) options.plugins.datalabels = { display: !pres.hide_datalabels };

        // Axis Display Toggles & Types
        if (pres.x_grid === false) options.scales.x.grid.display = false;
        if (pres.y_grid === false) options.scales.y.grid.display = false;
        if (pres.x_type) options.scales.x.type = pres.x_type;

        // Labels & Titles
        if (pres.x_labels) options.scales.x.labels = pres.x_labels;
        if (config.x_label) options.scales.x.title = { display: true, text: config.x_label, color: this.textColor };
        if (config.y_label) options.scales.y.title = { display: true, text: config.y_label, color: this.textColor };
        
        // Scaling & Fonts
        if (pres.y_min !== undefined) options.scales.y.suggestedMin = pres.y_min;
        if (pres.y_max !== undefined) options.scales.y.suggestedMax = pres.y_max;
        if (pres.tick_font_size) { 
            options.scales.x.ticks.font.size = pres.tick_font_size;
            options.scales.y.ticks.font.size = pres.tick_font_size;
        }

        // Dynamic Zero Line
        if (pres.draw_zero_line) {
            options.scales.x.grid = {
                color: (context) => context.tick.value === 0 ? this.zeroLineColor : 'transparent',
                lineWidth: (context) => context.tick.value === 0 ? 1 : 0
            };
        }

        // Dual Axis Configuration
        if (pres.has_dual_axis) {
            options.scales.y = { type: 'linear', position: 'left', title: { display: true, text: config.y_label, color: this.textColor } };
            options.scales.y1 = { type: 'linear', position: 'right', title: { display: true, text: config.y2_label, color: this.textColor }, grid: { drawOnChartArea: false } };
        }

        // Chart Type-Specific Native Overrides
        //  Bubble Chart Offest
        if (chartType === 'bubble') {
            options.scales.x.offset = true;
            options.scales.y.offset = true;
        }

        // Tooltip Configurations
        if (pres.tooltip_style === 'dual_axis') {
            options.plugins.tooltip.callbacks.label = function(context) {
                return `${context.dataset.label.split(' (')[0]}: ${context.raw.toFixed(2)}`;
            };
        } else if (pres.tooltip_style === 'bubble') {
            options.plugins.tooltip.callbacks.label = function(context) {
                let relScore = ((context.raw.r - 4) / 16).toFixed(2);
                return [`${context.dataset.label}:`, `| relatability - ${relScore}`, `| perception - ${context.raw.y}`];
            };
        }
    }

    // --- Palette Application ---
    applyColorMapping(dataPayload, pres) {
        const activePalette = this.palettes[pres.palette] || this.palettes['generic'];
        const colorMapping = pres.color_mapping || 'default';
        const customColors = pres.custom_colors || {};

        // helper to get DOM css
        const getCustomColor = (cssVar) => {
            return getComputedStyle(document.body).getPropertyValue(cssVar).trim() || cssVar;
        };

        dataPayload.datasets.forEach((dataset, index) => {
            // calculate base colour
            let baseColor = activePalette[index % activePalette.length];

            // apply json overrides
            if (customColors[dataset.label]) {
                baseColor = getCustomColor(customColors[dataset.label]);
            }

            if (colorMapping === 'gradient_index') {
                dataset.backgroundColor = dataset.data.map((_, i) => this.getColorFromPalette(activePalette, dataset.data.length > 1 ? i / (dataset.data.length - 1) : 0));
                dataset.borderColor = this.gridColor; dataset.borderWidth = 1; dataset.barPercentage = 0.95; dataset.categoryPercentage = 1.0;
            } 
            else if (colorMapping === 'gradient_value') {
                dataset.backgroundColor = dataset.data.map(val => this.getColorFromPalette(activePalette, (1 - Math.max(-1, Math.min(1, val))) / 2));
                dataset.borderColor = this.gridColor; dataset.borderWidth = 0; dataset.barPercentage = 0.95; dataset.categoryPercentage = 1.0;
            }
            else if (colorMapping === 'sequential') {
                dataset.backgroundColor = dataset.data.map((_, i) => activePalette[i % activePalette.length]);
                dataset.borderColor = this.gridColor; 
                dataset.borderWidth = 0; dataset.barPercentage = 0.85; dataset.categoryPercentage = 1.0;
            }
            else if (colorMapping === 'categorical_line') {
                dataset.backgroundColor = 'transparent';                    
                dataset.borderColor = baseColor;
                dataset.pointBackgroundColor = baseColor;
                dataset.pointStyle = index === 0 ? 'circle' : 'rect';       
                dataset.pointRadius = 5; dataset.pointHoverRadius = 8;
                dataset.borderWidth = 3; dataset.tension = 0.3;                                      
            } 
            else if (colorMapping === 'categorical_bubble') {
                dataset.backgroundColor = baseColor + '40';     // hex + '40' = 25% opacity                    
                dataset.borderColor = baseColor;
                dataset.borderWidth = 2;
            }
        });
    }

    render(config, dataPayload) {
        if (!this.ctx) return;
        this.clear();
        
        // get presentation configuration
        const pres = config.presentation || {};

        // fetch list of allowed/active Chart.js chart types.
        const chartJSTypes = Object.keys(Chart.registry.controllers.items);

        // console.log(`[Waymo Agent] Available Chart.js Types: \n${chartJSTypes}`)     // Testing

        // validate configuration type against Chart.js types
        let chartType = config.type;
        if (!chartJSTypes.includes(chartType)) {
            console.warn(`[Waymo Agent] Invalid chart type '${chartType}' requested. Falling back to 'bar'.`);
            chartType = 'bar';
        }
        
        // retrieve default options
        let options = this.defaultOptionsConfig(config);

        // apply override logic
        this.applyStructuralOverrides(options, pres, config, chartType);
        this.applyColorMapping(dataPayload, pres);
        
        // initialise chart instance
        this.chartInstance = new Chart(this.ctx, {
            type: chartType,
            data: dataPayload,
            options: options
        });
    }
}