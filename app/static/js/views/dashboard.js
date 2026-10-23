import { createPeriodPicker } from "../components/period-picker.js";
import { renderPortfolioCharts, resizePortfolioCharts } from "../components/portfolio-charts.js";
import { creditsApi, userMessage } from "../lib/api.js";
import { onCreditsChanged } from "../lib/events.js";
import {
    formatCurrency, formatDate, formatDayMonth, formatInteger, formatMonths, formatPercent, todayIso,
} from "../lib/format.js";
import { VIEW_SHOWN } from "../lib/router.js";

let summary = null;
let period = {};
let requestId = 0;
let openCredit = () => {};

export function initDashboard({ onView } = {}) {
    if (onView) openCredit = onView;
    createPeriodPicker({ onChange: setPeriod });

    document.getElementById("dashboard-retry").addEventListener("click", loadSummary);

    document.getElementById("upcoming-payments").addEventListener("click", event => {
        const button = event.target.closest("button[data-id]");
        if (button) openCredit(Number(button.dataset.id));
    });

    onCreditsChanged(loadSummary);
    // Charts drawn while their view was hidden need a resize once it is visible
    document.addEventListener(VIEW_SHOWN, event => {
        if (event.detail.view === "dashboard") resizePortfolioCharts();
    });
    loadSummary();

    // Charts read their colors from CSS variables, so they are rebuilt when the theme changes
    return { refreshTheme: () => summary && summary.total_credits > 0 && renderPortfolioCharts(summary) };
}

function setPeriod(range) {
    period = range;
    loadSummary();
}

async function loadSummary() {
    // A slower answer for an older period must not overwrite a newer one
    const current = ++requestId;
    const retry = document.getElementById("dashboard-retry");
    retry.disabled = true;
    try {
        const data = await creditsApi.summary(period);
        if (current !== requestId) return;
        summary = data;
        showError(null);
        render(summary);
    } catch (error) {
        if (current !== requestId) return;
        // Keep the last figures on screen, but say they could not be refreshed
        showError(error);
    } finally {
        if (current === requestId) retry.disabled = false;
    }
}

function showError(error) {
    document.getElementById("dashboard-error").hidden = !error;
    if (!error) return;
    const kept = summary ? " Se muestran los últimos datos cargados." : "";
    setText("dashboard-error-text", `${userMessage(error)}${kept}`);
}

function render(data) {
    const hasCredits = data.total_credits > 0;
    const total = Number(data.total_amount);
    const outstandingShare = total > 0 ? (Number(data.outstanding_balance) / total) * 100 : 0;

    setText("kpi-total-credits", formatInteger(data.total_credits));
    setText("kpi-credit-status", hasCredits
        ? [[data.active_credits, "vigente"], [data.overdue_credits, "atrasado"], [data.completed_credits, "concluido"]]
            .map(([count, word]) => `${formatInteger(count)} ${word}${count === 1 ? "" : "s"}`)
            .join(" · ")
        : "");
    setText("kpi-total-amount", formatCurrency(data.total_amount));
    setText("kpi-average-amount", hasCredits ? `Promedio de ${formatCurrency(data.average_amount)} por crédito` : "");
    setText("kpi-outstanding", formatCurrency(data.outstanding_balance));
    document.getElementById("kpi-outstanding-meter").style.width = `${outstandingShare}%`;
    setText("kpi-outstanding-share", hasCredits
        ? `${formatPercent(outstandingShare.toFixed(1))} del monto otorgado, según los pagos registrados`
        : "");
    const overdue = Number(data.overdue_amount) > 0;
    document.getElementById("kpi-overdue").hidden = !overdue;
    if (overdue) setText("kpi-overdue", `${formatCurrency(data.overdue_amount)} vencido sin pagar`);
    setText("kpi-weighted-rate", formatPercent(data.weighted_interest_rate));
    setText("kpi-rate-detail", hasCredits
        ? `Promedio simple ${formatPercent(data.average_interest_rate)} · plazo de ${formatMonths(data.average_term_months)}`
        : "");

    document.getElementById("dashboard-content").hidden = !hasCredits;
    document.getElementById("dashboard-empty").hidden = hasCredits;
    if (hasCredits) {
        renderPortfolioCharts(data);
        renderTopClients(data.top_clients);
        renderUpcoming(data.upcoming_payments);
    }
}

function renderUpcoming(payments) {
    const today = todayIso();
    const items = payments.map(payment => {
        const item = document.createElement("li");
        const button = document.createElement("button");
        button.type = "button";
        button.className = `upcoming-item${payment.overdue ? " is-overdue" : ""}`;
        button.dataset.id = payment.credit_id;
        const when = payment.overdue ? "vencido desde el" : "vence el";
        button.setAttribute("aria-label", `Ver crédito de ${payment.client_name}, ${when} ${formatDate(payment.due_date)}`);

        const [day, monthLabel] = formatDayMonth(payment.due_date);
        const dateBox = document.createElement("span");
        dateBox.className = "upcoming-date";
        dateBox.setAttribute("aria-hidden", "true");
        const dayText = document.createElement("strong");
        dayText.textContent = day;
        const monthText = document.createElement("span");
        monthText.textContent = monthLabel;
        dateBox.append(dayText, monthText);

        const info = document.createElement("span");
        info.className = "upcoming-info";
        const name = document.createElement("span");
        name.className = "upcoming-name";
        name.textContent = payment.client_name;
        const due = document.createElement("span");
        due.className = "upcoming-due";
        due.textContent = dueLabel(daysBetween(today, payment.due_date));
        info.append(name, due);

        const amount = document.createElement("span");
        amount.className = "upcoming-amount";
        amount.textContent = formatCurrency(payment.amount);

        button.append(dateBox, info, amount);
        item.appendChild(button);
        return item;
    });
    document.getElementById("upcoming-payments").replaceChildren(...items);
    document.getElementById("upcoming-empty").hidden = payments.length > 0;
}

// Whole days between two ISO dates, read as UTC so time zones never shift them
function daysBetween(fromIso, toIso) {
    return Math.round((Date.parse(`${toIso}T00:00:00Z`) - Date.parse(`${fromIso}T00:00:00Z`)) / 86400000);
}

function dueLabel(days) {
    if (days < 0) return days === -1 ? "Vencido hace 1 día" : `Vencido hace ${-days} días`;
    if (days === 0) return "Vence hoy";
    if (days === 1) return "Vence mañana";
    return `Vence en ${days} días`;
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

function setText(id, text) {
    document.getElementById(id).textContent = text;
}
