// Dashboard charts; Chart.js is loaded globally from the CDN in base.html
import { formatCompactCurrency, formatCurrency, formatMonth } from "../lib/format.js";

// API term buckets and the labels shown to the user
const TERM_LABELS = {
    "1-12": "Hasta 12 meses",
    "13-24": "13 a 24 meses",
    "25-36": "25 a 36 meses",
    "37+": "Más de 36 meses",
};

const charts = {};

export function renderPortfolioCharts(data) {
    const css = getComputedStyle(document.documentElement);
    const color = name => css.getPropertyValue(name).trim();
    const palette = ["--app-chart-1", "--app-chart-2", "--app-chart-3", "--app-chart-4"].map(color);

    Chart.defaults.color = color("--bs-secondary-color");
    Chart.defaults.font.family = color("--bs-body-font-family");

    drawChart("monthly", "monthly-chart", {
        type: "bar",
        data: {
            labels: data.monthly.map(item => formatMonth(item.year, item.month)),
            datasets: [{
                label: "Monto otorgado",
                data: data.monthly.map(item => Number(item.total_amount)),
                backgroundColor: palette[0],
                borderRadius: 6,
                maxBarThickness: 42,
            }],
        },
        options: {
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: context => {
                            const credits = data.monthly[context.dataIndex].credits;
                            return `${formatCurrency(context.parsed.y)} · ${credits} ${credits === 1 ? "crédito" : "créditos"}`;
                        },
                    },
                },
            },
            scales: {
                x: { grid: { display: false } },
                y: {
                    beginAtZero: true,
                    grid: { color: color("--app-border") },
                    border: { display: false },
                    ticks: { callback: formatCompactCurrency },
                },
            },
        },
    });

    drawChart("term", "term-chart", {
        type: "doughnut",
        data: {
            labels: data.by_term.map(item => TERM_LABELS[item.range] ?? item.range),
            datasets: [{
                data: data.by_term.map(item => item.credits),
                backgroundColor: palette,
                borderColor: color("--app-surface"),
                borderWidth: 3,
            }],
        },
        options: {
            maintainAspectRatio: false,
            cutout: "62%",
            plugins: {
                legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 8, padding: 14 } },
                tooltip: { callbacks: { label: context => ` ${context.label}: ${context.parsed}` } },
            },
        },
    });
}

function drawChart(key, canvasId, config) {
    charts[key]?.destroy();
    charts[key] = new Chart(document.getElementById(canvasId), config);
}

// Fits the charts to their boxes again (they measure zero while their view is hidden)
export function resizePortfolioCharts() {
    Object.values(charts).forEach(chart => chart.resize());
}
