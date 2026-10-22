import { creditsApi } from "../api.js";
import { onCreditsChanged } from "../events.js";
import {
    formatCompactCurrency, formatCurrency, formatDate, formatInteger, formatMonth, formatMonths, formatPercent, todayIso,
} from "../format.js";
import { VIEW_SHOWN } from "../router.js";

// API term buckets and the labels shown to the user
const TERM_LABELS = {
    "1-12": "Hasta 12 meses",
    "13-24": "13 a 24 meses",
    "25-36": "25 a 36 meses",
    "37+": "Más de 36 meses",
};

let summary = null;
let period = {};
const charts = {};

// Each preset returns the issue-date range sent to the API
const PRESETS = {
    all: () => ({}),
    year: () => {
        const year = todayIso().slice(0, 4);
        return { issue_date_from: `${year}-01-01`, issue_date_to: `${year}-12-31` };
    },
    last12: () => {
        const today = todayIso();
        const [year, month] = today.split("-").map(Number);
        // From the first day of the month 11 months ago, so 12 calendar months are covered
        const start = new Date(Date.UTC(year, month - 12, 1)).toISOString().slice(0, 10);
        return { issue_date_from: start, issue_date_to: today };
    },
};

export function initDashboard() {
    const presetButtons = document.querySelectorAll("[data-period]");
    const customForm = document.getElementById("period-form");

    presetButtons.forEach(button => button.addEventListener("click", () => {
        presetButtons.forEach(other => {
            other.classList.toggle("active", other === button);
            other.setAttribute("aria-pressed", String(other === button));
        });
        const preset = button.dataset.period;
        customForm.hidden = preset !== "custom";
        if (preset === "custom") {
            document.getElementById("period-from").focus();
            return;
        }
        setPeriod(PRESETS[preset]());
    }));

    customForm.addEventListener("submit", event => {
        event.preventDefault();
        const from = document.getElementById("period-from").value;
        const to = document.getElementById("period-to").value;
        if (!from || !to || from > to) {
            document.getElementById("period-label").textContent = "Elige una fecha inicial anterior o igual a la final.";
            return;
        }
        setPeriod({ issue_date_from: from, issue_date_to: to });
    });

    onCreditsChanged(loadSummary);
    // Charts drawn while their view was hidden need a resize once it is visible
    document.addEventListener(VIEW_SHOWN, event => {
        if (event.detail.view === "dashboard") Object.values(charts).forEach(chart => chart.resize());
    });
    loadSummary();

    // Charts read their colors from CSS variables, so they are rebuilt when the theme changes
    return { refreshTheme: () => summary && summary.total_credits > 0 && renderCharts(summary) };
}

function setPeriod(range) {
    period = range;
    loadSummary();
}

function periodLabel() {
    if (!period.issue_date_from) return "Todo el historial";
    return `${formatDate(period.issue_date_from)} – ${formatDate(period.issue_date_to)}`;
}

async function loadSummary() {
    try {
        summary = await creditsApi.summary(period);
        render(summary);
    } catch (error) {
        // The dashboard is secondary; keep the last data instead of interrupting the user
        console.error("Could not load the credit summary", error);
    }
}

function render(data) {
    document.getElementById("period-label").textContent = periodLabel();
    setText("kpi-total-credits", formatInteger(data.total_credits));
    setText("kpi-total-amount", formatCurrency(data.total_amount));
    setText("kpi-average-amount", data.total_credits ? `Promedio de ${formatCurrency(data.average_amount)} por crédito` : "");
    setText("kpi-average-rate", formatPercent(data.average_interest_rate));
    setText("kpi-average-term", formatMonths(data.average_term_months));

    const isEmpty = data.total_credits === 0;
    document.getElementById("dashboard-content").hidden = isEmpty;
    document.getElementById("dashboard-empty").hidden = !isEmpty;
    if (!isEmpty) {
        renderCharts(data);
        renderTopClients(data.top_clients);
    }
}

function renderTopClients(clients) {
    const highest = Number(clients[0]?.total_amount ?? 0);
    const items = clients.map((client, index) => {
        const item = document.createElement("li");
        item.className = "top-client";

        const rank = document.createElement("span");
        rank.className = "top-client-rank";
        rank.textContent = index + 1;

        const info = document.createElement("div");
        const name = document.createElement("div");
        name.className = "top-client-name";
        name.textContent = client.client_name;
        const meta = document.createElement("div");
        meta.className = "top-client-meta";
        meta.textContent = `${client.credits} ${client.credits === 1 ? "crédito" : "créditos"}`;
        info.append(name, meta);

        const amount = document.createElement("span");
        amount.className = "top-client-amount";
        amount.textContent = formatCurrency(client.total_amount);

        const bar = document.createElement("div");
        bar.className = "top-client-bar";
        bar.setAttribute("aria-hidden", "true");
        const fill = document.createElement("span");
        fill.style.width = `${highest ? (Number(client.total_amount) / highest) * 100 : 0}%`;
        bar.appendChild(fill);

        item.append(rank, info, amount, bar);
        return item;
    });
    document.getElementById("top-clients").replaceChildren(...items);
}

function renderCharts(data) {
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

function setText(id, text) {
    document.getElementById(id).textContent = text;
}
