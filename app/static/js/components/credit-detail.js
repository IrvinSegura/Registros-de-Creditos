import { creditsApi, userMessage } from "../lib/api.js";
import { deleteCredit } from "../lib/credit-actions.js";
import { onCreditsChanged } from "../lib/events.js";
import { formatCurrency, formatDate, formatDateTime, formatMonths, formatPercent, initials } from "../lib/format.js";
import { notifyError } from "../lib/notify.js";

// Field names and value formats shown in the change history
const FIELD_LABELS = {
    client_name: "Cliente",
    amount: "Monto",
    interest_rate: "Tasa anual",
    term_months: "Plazo",
    issue_date: "Fecha de otorgamiento",
};
const FIELD_FORMATS = {
    amount: formatCurrency,
    interest_rate: formatPercent,
    term_months: formatMonths,
    issue_date: formatDate,
};

export function initCreditDetail({ onEdit }) {
    const panelElement = document.getElementById("credit-detail");
    const panel = bootstrap.Offcanvas.getOrCreateInstance(panelElement);
    const element = id => document.getElementById(id);
    let credit = null;

    async function load(id) {
        const [data, schedule, history] = await Promise.all([
            creditsApi.get(id), creditsApi.amortization(id), creditsApi.history(id),
        ]);
        credit = data;
        renderSummary(data, schedule);
        renderProgress(data);
        renderSchedule(schedule.installments, data.standing);
        renderHistory(history);
    }

    function renderSummary(data, schedule) {
        element("detail-avatar").textContent = initials(data.client_name);
        element("credit-detail-title").textContent = data.client_name;
        element("detail-subtitle").textContent = `Crédito #${data.id} · otorgado el ${formatDate(data.issue_date)}`;
        element("detail-amount").textContent = formatCurrency(data.amount);
        element("detail-rate").textContent = formatPercent(data.interest_rate);
        element("detail-term").textContent = formatMonths(data.term_months);
        element("detail-payment").textContent = formatCurrency(schedule.monthly_payment);
        element("detail-interest").textContent = formatCurrency(schedule.total_interest);
        element("detail-total").textContent = formatCurrency(schedule.total_paid);
    }

    function renderProgress(data) {
        const { standing } = data;
        const completed = standing.status === "completed";
        const status = element("detail-status");
        status.textContent = completed ? "Concluido" : "Vigente";
        status.className = `badge rounded-pill status-badge ${completed ? "status-completed" : "status-active"}`;

        element("detail-progress-label").textContent = `${standing.installments_elapsed} de ${data.term_months} cuotas`;
        const bar = element("detail-progress-bar");
        bar.setAttribute("aria-valuemax", String(data.term_months));
        bar.setAttribute("aria-valuenow", String(standing.installments_elapsed));
        bar.classList.toggle("is-completed", completed);
        element("detail-progress-fill").style.width = `${(standing.installments_elapsed / data.term_months) * 100}%`;
        element("detail-outstanding").textContent = formatCurrency(standing.outstanding_balance);
        element("detail-next").textContent = completed
            ? "Sin cuotas pendientes"
            : `${formatDate(standing.next_due_date)} · ${formatCurrency(standing.next_payment)}`;
    }

    // Elapsed installments are muted and the next one is highlighted
    function renderSchedule(installments, standing) {
        const rows = installments.map(item => {
            const row = document.createElement("tr");
            if (item.number <= standing.installments_elapsed) row.className = "is-elapsed";
            if (item.number === standing.installments_elapsed + 1) row.className = "is-next";
            [
                [item.number, ""],
                [formatDate(item.due_date), ""],
                [formatCurrency(item.payment), "text-end"],
                [formatCurrency(item.interest), "text-end"],
                [formatCurrency(item.principal), "text-end"],
                [formatCurrency(item.balance), "text-end fw-semibold"],
            ].forEach(([text, className]) => {
                const cell = document.createElement("td");
                cell.className = className;
                cell.textContent = text;
                row.appendChild(cell);
            });
            return row;
        });
        element("detail-schedule-body").replaceChildren(...rows);
    }

    // Brings the next installment into view inside the scrollable schedule
    function scrollToNextInstallment() {
        const wrapper = element("detail-schedule-body").closest(".schedule-wrapper");
        const next = wrapper.querySelector("tr.is-next");
        const header = wrapper.querySelector("thead").offsetHeight;
        wrapper.scrollTop = next ? next.offsetTop - header - next.offsetHeight : 0;
    }

    function renderHistory(entries) {
        element("detail-history-count").textContent = entries.length || "";
        element("detail-history-empty").hidden = entries.length > 0;
        element("detail-history-list").replaceChildren(...entries.map(buildHistoryItem));
    }

    // The buttons are only rendered for roles that may edit or delete
    element("detail-edit")?.addEventListener("click", () => credit && onEdit?.(credit.id));
    element("detail-delete")?.addEventListener("click", async () => {
        if (credit && await deleteCredit(credit.id, credit.client_name)) panel.hide();
    });

    // Keep the open panel in sync after edits made from the modal or the table
    onCreditsChanged(async () => {
        if (!credit || !panelElement.classList.contains("show")) return;
        try {
            await load(credit.id);
        } catch (error) {
            panel.hide();
        }
    });

    return {
        async open(id) {
            try {
                await load(id);
                bootstrap.Tab.getOrCreateInstance(element("detail-schedule-tab")).show();
                panel.show();
                scrollToNextInstallment();
            } catch (error) {
                notifyError(userMessage(error), "No se pudo abrir el crédito");
            }
        },
    };
}

function buildHistoryItem(entry) {
    const created = entry.action === "created";
    const item = document.createElement("li");
    item.className = "timeline-item";

    const icon = document.createElement("span");
    icon.className = `timeline-icon${created ? " timeline-icon-created" : ""}`;
    icon.setAttribute("aria-hidden", "true");
    const iconGlyph = document.createElement("i");
    iconGlyph.className = created ? "bi bi-plus-lg" : "bi bi-pencil";
    icon.appendChild(iconGlyph);

    const content = document.createElement("div");
    const title = document.createElement("p");
    title.className = "timeline-title";
    title.textContent = created ? "Crédito registrado" : "Crédito actualizado";
    const date = document.createElement("p");
    date.className = "timeline-date";
    // Entries recorded before sign-in existed have no author
    date.textContent = entry.changed_by
        ? `${formatDateTime(entry.changed_at)} · por ${entry.changed_by}`
        : formatDateTime(entry.changed_at);
    content.append(title, date);

    // Creations list the original values; updates list what changed
    const list = document.createElement("ul");
    list.className = "timeline-changes";
    Object.entries(entry.changes).forEach(([field, change]) => list.appendChild(buildChange(field, change)));
    content.appendChild(list);

    item.append(icon, content);
    return item;
}

function buildChange(field, { old: oldValue, new: newValue }) {
    const format = FIELD_FORMATS[field] ?? (value => value);
    const item = document.createElement("li");
    const label = document.createElement("span");
    label.textContent = `${FIELD_LABELS[field] ?? field}: `;
    const newText = document.createElement("span");
    newText.className = "new-value";
    newText.textContent = format(newValue);
    item.appendChild(label);

    if (oldValue !== null && oldValue !== undefined) {
        const oldText = document.createElement("span");
        oldText.className = "old-value";
        oldText.textContent = format(oldValue);
        item.append(oldText, document.createTextNode(" → "));
    }
    item.appendChild(newText);
    return item;
}
