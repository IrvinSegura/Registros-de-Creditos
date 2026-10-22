import { creditsApi } from "../api.js";
import { onCreditsChanged } from "../events.js";
import { formatCompactCurrency, formatCurrency, formatInteger, formatMonth, formatMonths, formatPercent } from "../format.js";

// API term buckets and the labels shown to the user
const TERM_LABELS = {
    "1-12": "Hasta 12 meses",
    "13-24": "13 a 24 meses",
    "25-36": "25 a 36 meses",
    "37+": "Más de 36 meses",
};

let summary = null;
const charts = {};

export function initStats() {
    onCreditsChanged(loadSummary);
    loadSummary();
    // Charts read their colors from CSS variables, so they are rebuilt when the theme changes
    return { refreshTheme: () => summary && renderCharts(summary) };
}

async function loadSummary() {
    try {
        summary = await creditsApi.summary();
        render(summary);
    } catch (error) {
        // The dashboard is secondary; keep the last data instead of interrupting the user
        console.error("Could not load the credit summary", error);
    }
}

function render(data) {
    setText("kpi-total-credits", formatInteger(data.total_credits));
    setText("kpi-total-amount", formatCurrency(data.total_amount));
    setText("kpi-average-amount", data.total_credits ? `Promedio de ${formatCurrency(data.average_amount)} por crédito` : "");
    setText("kpi-average-rate", formatPercent(data.average_interest_rate));
    setText("kpi-average-term", formatMonths(data.average_term_months));

    const isEmpty = data.total_credits === 0;
    document.getElementById("stats-charts").classList.toggle("d-none", isEmpty);
    document.getElementById("stats-empty").classList.toggle("d-none", !isEmpty);
    if (!isEmpty) renderCharts(data);
}

function renderCharts(data) {
    const css = getComputedStyle(document.documentElement);
    const color = name => css.getPropertyValue(name).trim();
    const palette = ["--app-chart-1", "--app-chart-2", "--app-chart-3", "--app-chart-4"].map(color);
    const textColor = color("--bs-secondary-color");
    const gridColor = color("--app-border");
    const fontFamily = color("--bs-body-font-family");

    Chart.defaults.color = textColor;
    Chart.defaults.font.family = fontFamily;

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
                y: { beginAtZero: true, grid: { color: gridColor }, border: { display: false }, ticks: { callback: formatCompactCurrency } },
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

function setText(id, text) {
    document.getElementById(id).textContent = text;
}
