/**
 * File: analytics.js
 * Title: Data Visualisation & Dashboard Controller
 * Description: Manages Chart.js rendering, data filtering, and AI Narrative UI.
 */

document.addEventListener("DOMContentLoaded", async () => {
    
    // 1. sidebar tab navigation logic
    const sidebarBtns   = document.querySelectorAll(".sidebar-btn");
    const sections      = document.querySelectorAll(".settings-section");

    sidebarBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            sidebarBtns.forEach(b => b.classList.remove("active"));
            sections.forEach(s => s.classList.add("hidden"));

            btn.classList.add("active");

            document.getElementById(btn.getAttribute("data-target")).classList.remove("hidden");
        });
    });

    // 2. chart.js initialization
    let overviewChart = null;

    async function loadGraphData() {
        const timeFilter = document.getElementById("graph-time-filter").value;
        const typeFilter = document.getElementById("graph-type-filter").value;
        
        // Get active data sources from checkboxes
        const activeSources = Array.from(document.querySelectorAll('.source-toggle:checked')).map(cb => cb.value);

        try {
            // We will build this endpoint in the backend shortly
            // const rawData = await window.API.getGraphData(timeFilter, activeSources);
            
            // --- MOCK DATA FOR UI TESTING (Until DB is updated in Phase 2) ---
            const labels = ["Day 1", "Day 2", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"];
            const sentimentData = [0.2, 0.4, -0.1, -0.5, 0.3, 0.6, 0.8]; // -1.0 to 1.0
            const volumeData = [12, 19, 45, 60, 22, 15, 30]; 

            renderChart(labels, sentimentData, volumeData, typeFilter);

        } catch (error) {
            console.error("Failed to load graph data", error);
        }
    }

    function renderChart(labels, sentiment, volume, chartType) {
        const ctx = document.getElementById('overviewChart').getContext('2d');
        
        // Destroy existing chart if updating
        if (overviewChart) {
            overviewChart.destroy();
        }

        // Determine colors based on current CSS theme variables
        const style = getComputedStyle(document.body);
        const accentColor = style.getPropertyValue('--accent-color').trim() || '#0066cc';
        const textColor = style.getPropertyValue('--text-primary').trim() || '#1a1a1a';
        const gridColor = style.getPropertyValue('--border-color').trim() || '#e0e0e0';

        overviewChart = new Chart(ctx, {
            type: chartType, // 'line' or 'bar'
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Avg Sentiment (-1 to 1)',
                        data: sentiment,
                        borderColor: accentColor,
                        backgroundColor: chartType === 'bar' ? accentColor : 'transparent',
                        borderWidth: 2,
                        tension: 0.3, // smooth curves
                        yAxisID: 'y'
                    },
                    {
                        label: 'Post Volume',
                        data: volume,
                        borderColor: '#888888',
                        backgroundColor: 'rgba(136, 136, 136, 0.2)',
                        borderWidth: 2,
                        type: 'bar', // Volume is usually best as a bar behind the line
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                color: textColor,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    x: {
                        grid: { color: gridColor }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: { display: true, text: 'Sentiment Score' },
                        min: -1,
                        max: 1,
                        grid: { color: gridColor }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: { display: true, text: 'Volume' },
                        grid: { drawOnChartArea: false } // keep grid clean
                    }
                }
            }
        });
    }

    // 3. Attach Event Listeners to Controls
    document.getElementById("graph-time-filter").addEventListener("change", loadGraphData);
    document.getElementById("graph-type-filter").addEventListener("change", loadGraphData);
    document.querySelectorAll('.source-toggle').forEach(cb => {
        cb.addEventListener("change", loadGraphData);
    });

    // 4. Initial Render
    loadGraphData();
});