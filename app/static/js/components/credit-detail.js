import { creditsApi, userMessage } from "../lib/api.js";
import { archiveCredit, deleteCreditForGood, restoreCredit } from "../lib/credit-actions.js";
import { notifyCreditsChanged, onCreditsChanged } from "../lib/events.js";
import { formatCurrency, formatDate, formatDateTime, formatMonths, formatPercent, initials, todayIso } from "../lib/format.js";
import { clearValidation, handleFormError, validateField, validateForm, withBusyButton } from "../lib/forms.js";
import { confirmDanger, notifyError, notifySuccess } from "../lib/notify.js";
import { can, PERMISSIONS } from "../lib/session.js";
import { VIEW_SHOWN } from "../lib/router.js";
import { creditStatus, statusLabel } from "../lib/status.js";

// Field names and value formats shown in the change history
const FIELD_LABELS = {
    client_name: "Cliente",
    amount: "Monto",
    interest_rate: "Tasa anual",
    term_months: "Plazo",
    issue_date: "Fecha de otorgamiento",
    paid_on: "Fecha de pago",
    note: "Nota",
};
const FIELD_FORMATS = {
    amount: formatCurrency,
    interest_rate: formatPercent,
    term_months: formatMonths,
    issue_date: formatDate,
    paid_on: formatDate,
};
// Title and icon of each kind of history entry
const HISTORY_ENTRIES = {
    created: ["Crédito registrado", "bi-plus-lg", "timeline-icon-created"],
    updated: ["Crédito actualizado", "bi-pencil", ""],
    archived: ["Crédito archivado", "bi-archive", "timeline-icon-muted"],
    restored: ["Crédito restaurado", "bi-arrow-counterclockwise", ""],
    payment: ["Pago registrado", "bi-cash-coin", "timeline-icon-created"],
    payment_removed: ["Pago eliminado", "bi-x-lg", "timeline-icon-danger"],
};
const INSTALLMENT_LABELS = { paid: "Pagada", overdue: "Vencida", pending: "Pendiente" };

export function initCreditDetail({ onEdit }) {
    const panelElement = document.getElementById("credit-detail");
    const panel = bootstrap.Offcanvas.getOrCreateInstance(panelElement);
    const element = id => document.getElementById(id);
    const paymentForm = element("payment-form");
    let credit = null;

    async function load(id) {
        const [data, schedule, history, payments] = await Promise.all([
            creditsApi.get(id), creditsApi.amortization(id), creditsApi.history(id), creditsApi.payments(id),
        ]);
        credit = data;
        renderSummary(data, schedule);
        renderProgress(data);
        renderSchedule(schedule.installments);
        renderPayments(payments, data);
        renderHistory(history);
        renderActions(data);
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
        const status = creditStatus(data);
        const badge = element("detail-status");
        badge.textContent = statusLabel(status);
        badge.className = `badge rounded-pill status-badge status-${status}`;
        element("detail-archived").hidden = status !== "archived";

        const overdue = standing.status === "overdue";
        element("detail-overdue").hidden = !overdue;
        if (overdue) {
            const installments = standing.overdue_installments === 1 ? "1 cuota vencida" : `${standing.overdue_installments} cuotas vencidas`;
            const days = standing.days_overdue === 1 ? "1 día" : `${standing.days_overdue} días`;
            element("detail-overdue-text").textContent =
                `${installments} sin pagar por ${formatCurrency(standing.overdue_amount)} · ${days} de atraso.`;
        }

        element("detail-progress-label").textContent = `${standing.installments_paid} de ${data.term_months} cuotas pagadas`;
        const bar = element("detail-progress-bar");
        bar.setAttribute("aria-valuemax", String(data.term_months));
        bar.setAttribute("aria-valuenow", String(standing.installments_paid));
        bar.classList.toggle("is-completed", standing.status === "completed");
        bar.classList.toggle("is-overdue", overdue);
        element("detail-progress-fill").style.width = `${(standing.installments_paid / data.term_months) * 100}%`;
        element("detail-paid").textContent = formatCurrency(standing.paid_total);
        element("detail-remaining").textContent = formatCurrency(standing.remaining_total);
        element("detail-outstanding").textContent = formatCurrency(standing.outstanding_balance);
        element("detail-next").textContent = standing.next_due_date
            ? `${formatDate(standing.next_due_date)} · ${formatCurrency(standing.next_payment)}`
            : "Sin pagos pendientes";
    }

    // Paid installments are muted, overdue ones are marked and the first unpaid one is highlighted
    function renderSchedule(installments) {
        const next = installments.find(item => item.status !== "paid");
        const rows = installments.map(item => {
            const row = document.createElement("tr");
            row.className = `is-${item.status}${item === next ? " is-next" : ""}`;
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
            const statusCell = document.createElement("td");
            const label = document.createElement("span");
            label.className = `installment-status installment-${item.status}`;
            label.textContent = INSTALLMENT_LABELS[item.status];
            statusCell.appendChild(label);
            row.appendChild(statusCell);
            return row;
        });
        element("detail-schedule-body").replaceChildren(...rows);
    }

    // Brings the first unpaid installment into view inside the scrollable schedule
    function scrollToNextInstallment() {
        const wrapper = element("detail-schedule-body").closest(".schedule-wrapper");
        const next = wrapper.querySelector("tr.is-next");
        const header = wrapper.querySelector("thead").offsetHeight;
        wrapper.scrollTop = next ? next.offsetTop - header - next.offsetHeight : 0;
    }

    function renderPayments(payments, data) {
        element("detail-payments-count").textContent = payments.length || "";
        element("detail-payments-empty").hidden = payments.length > 0;
        element("detail-payments-list").replaceChildren(...payments.map(payment => buildPaymentItem(payment, data)));
        if (!paymentForm) return;

        // Payments go to credits in the portfolio that still owe something
        const open = !data.archived_at && data.standing.status !== "completed";
        paymentForm.hidden = !open;
        if (!open) return;
        clearValidation(paymentForm);
        const { standing } = data;
        // Suggest what is due now: the overdue amount, or what is left of the next installment
        const suggested = standing.status === "overdue" ? standing.overdue_amount : standing.next_payment;
        paymentForm.elements.amount.value = suggested;
        paymentForm.elements.amount.max = standing.remaining_total;
        paymentForm.elements.paid_on.value = todayIso();
        paymentForm.elements.paid_on.min = data.issue_date;
        paymentForm.elements.paid_on.max = todayIso();
        paymentForm.elements.note.value = "";
        element("payment-amount-hint").textContent = `Falta por pagar ${formatCurrency(standing.remaining_total)}`;
    }

    function renderHistory(entries) {
        element("detail-history-count").textContent = entries.length || "";
        element("detail-history-empty").hidden = entries.length > 0;
        element("detail-history-list").replaceChildren(...entries.map(buildHistoryItem));
    }

    // Which buttons apply depends on whether the credit is archived; the role decided which exist
    function renderActions(data) {
        const archived = Boolean(data.archived_at);
        const show = (id, visible) => { if (element(id)) element(id).hidden = !visible; };
        show("detail-edit", !archived);
        show("detail-archive", !archived);
        show("detail-restore", archived);
        show("detail-delete", archived);
        document.querySelectorAll("[data-statement]").forEach(link => {
            link.href = creditsApi.statementUrl(data.id, link.dataset.statement);
        });
    }

    paymentForm?.addEventListener("input", event => validateField(event.target));
    paymentForm?.addEventListener("submit", async event => {
        event.preventDefault();
        if (!credit || !validateForm(paymentForm)) return;
        const submitButton = paymentForm.querySelector("button[type='submit']");
        await withBusyButton(submitButton, async () => {
            try {
                await creditsApi.addPayment(credit.id, {
                    amount: paymentForm.elements.amount.value.trim(),
                    paid_on: paymentForm.elements.paid_on.value,
                    note: paymentForm.elements.note.value.trim(),
                });
                notifySuccess("Pago registrado");
                notifyCreditsChanged();
            } catch (error) {
                handleFormError(paymentForm, error);
            }
        });
    });

    element("detail-payments-list").addEventListener("click", async event => {
        const button = event.target.closest("button[data-payment-id]");
        if (!button || !credit) return;
        const confirmed = await confirmDanger({
            title: "¿Eliminar este pago?",
            text: `Se quitará el pago de ${button.dataset.amount} del ${button.dataset.date}. El historial conservará el registro.`,
            confirmText: "Sí, eliminar pago",
        });
        if (!confirmed) return;
        try {
            await creditsApi.removePayment(credit.id, button.dataset.paymentId);
            notifySuccess("Pago eliminado");
            notifyCreditsChanged();
        } catch (error) {
            notifyError(userMessage(error));
        }
    });

    // The buttons are only rendered for roles that may use them
    element("detail-edit")?.addEventListener("click", () => credit && onEdit?.(credit.id));
    element("detail-archive")?.addEventListener("click", () => credit && archiveCredit(credit.id, credit.client_name));
    element("detail-restore")?.addEventListener("click", () => credit && restoreCredit(credit.id));
    element("detail-delete")?.addEventListener("click", async () => {
        if (credit && await deleteCreditForGood(credit.id, credit.client_name)) panel.hide();
    });

    // The panel belongs to the view it was opened from; going to another view closes it
    document.addEventListener(VIEW_SHOWN, () => panel.hide());

    // Keep the open panel in sync after changes made here, from the modal or from the table
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

function buildPaymentItem(payment, credit) {
    const item = document.createElement("li");
    item.className = "payment-item";

    const icon = document.createElement("span");
    icon.className = "payment-icon";
    icon.setAttribute("aria-hidden", "true");
    const glyph = document.createElement("i");
    glyph.className = "bi bi-cash-coin";
    icon.appendChild(glyph);

    const info = document.createElement("div");
    info.className = "payment-info";
    const amount = document.createElement("p");
    amount.className = "payment-amount";
    amount.textContent = formatCurrency(payment.amount);
    const meta = document.createElement("p");
    meta.className = "payment-meta";
    // Payments carried over when payment tracking started have no author
    meta.textContent = payment.recorded_by
        ? `${formatDate(payment.paid_on)} · registró ${payment.recorded_by}`
        : formatDate(payment.paid_on);
    info.append(amount, meta);
    if (payment.note) {
        const note = document.createElement("p");
        note.className = "payment-note";
        note.textContent = payment.note;
        info.appendChild(note);
    }
    item.append(icon, info);

    if (can(PERMISSIONS.deletePayments) && !credit.archived_at) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "btn btn-sm btn-outline-danger ms-auto";
        button.dataset.paymentId = payment.id;
        button.dataset.amount = formatCurrency(payment.amount);
        button.dataset.date = formatDate(payment.paid_on);
        const label = `Eliminar pago de ${formatCurrency(payment.amount)} del ${formatDate(payment.paid_on)}`;
        button.title = label;
        button.setAttribute("aria-label", label);
        const trash = document.createElement("i");
        trash.className = "bi bi-trash3";
        trash.setAttribute("aria-hidden", "true");
        button.appendChild(trash);
        item.appendChild(button);
    }
    return item;
}

function buildHistoryItem(entry) {
    const [titleText, iconName, iconClass] = HISTORY_ENTRIES[entry.action] ?? HISTORY_ENTRIES.updated;
    const item = document.createElement("li");
    item.className = "timeline-item";

    const icon = document.createElement("span");
    icon.className = `timeline-icon ${iconClass}`.trim();
    icon.setAttribute("aria-hidden", "true");
    const iconGlyph = document.createElement("i");
    iconGlyph.className = `bi ${iconName}`;
    icon.appendChild(iconGlyph);

    const content = document.createElement("div");
    const title = document.createElement("p");
    title.className = "timeline-title";
    title.textContent = titleText;
    const date = document.createElement("p");
    date.className = "timeline-date";
    // Entries recorded before sign-in existed have no author
    date.textContent = entry.changed_by
        ? `${formatDateTime(entry.changed_at)} · por ${entry.changed_by}`
        : formatDateTime(entry.changed_at);
    content.append(title, date);

    // Creations and payments list their values; updates list what changed
    const changes = Object.entries(entry.changes);
    if (changes.length) {
        const list = document.createElement("ul");
        list.className = "timeline-changes";
        changes.forEach(([field, change]) => list.appendChild(buildChange(field, change)));
        content.appendChild(list);
    }

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
