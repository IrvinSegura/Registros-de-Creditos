// Rows of the credits table, built with textContent so user data is never parsed as HTML
import { formatCurrency, formatDate, formatMonths, formatPercent, initials } from "../lib/format.js";
import { can, PERMISSIONS } from "../lib/session.js";
import { buildStatusBadge, creditStatus } from "../lib/status.js";

const COLUMNS = 7;

export function buildCreditRow(credit) {
    const row = document.createElement("tr");

    const client = document.createElement("td");
    client.className = "cell-client";
    client.dataset.label = "Cliente";
    const clientButton = document.createElement("button");
    clientButton.type = "button";
    clientButton.className = "client-link";
    clientButton.dataset.action = "view";
    clientButton.dataset.id = credit.id;
    const avatar = document.createElement("span");
    avatar.className = "avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = initials(credit.client_name);
    const name = document.createElement("span");
    name.className = "client-name";
    name.textContent = credit.client_name;
    clientButton.append(avatar, name);
    client.appendChild(clientButton);

    const term = document.createElement("td");
    term.dataset.label = "Plazo";
    term.appendChild(buildProgress(credit));

    const status = creditStatus(credit);
    const balance = textCell(formatCurrency(credit.standing.outstanding_balance), "text-end numeric", "Saldo pendiente");
    if (status === "completed" || status === "archived") balance.classList.add("text-body-secondary");
    if (status === "overdue") {
        const overdue = document.createElement("span");
        overdue.className = "balance-overdue";
        overdue.textContent = `Vencido ${formatCurrency(credit.standing.overdue_amount)}`;
        balance.appendChild(overdue);
    }

    const actions = document.createElement("td");
    actions.className = "text-end cell-actions";
    const actionGroup = document.createElement("div");
    actionGroup.className = "row-actions";
    actionGroup.append(
        actionButton("view", "btn-outline-secondary", "bi-eye", `Ver detalle del crédito de ${credit.client_name}`, credit),
    );
    // Archived credits are read-only: they can only be viewed or restored
    if (can(PERMISSIONS.update) && status !== "archived") {
        actionGroup.append(
            actionButton("edit", "btn-outline-primary", "bi-pencil", `Editar crédito de ${credit.client_name}`, credit),
        );
    }
    if (can(PERMISSIONS.archive)) {
        actionGroup.append(status === "archived"
            ? actionButton("restore", "btn-outline-secondary", "bi-arrow-counterclockwise",
                `Restaurar crédito de ${credit.client_name}`, credit)
            : actionButton("archive", "btn-outline-secondary", "bi-archive", `Archivar crédito de ${credit.client_name}`, credit));
    }
    actions.appendChild(actionGroup);

    row.append(
        client,
        textCell(formatCurrency(credit.amount), "text-end numeric fw-semibold", "Monto"),
        textCell(formatPercent(credit.interest_rate), "text-end numeric", "Tasa anual"),
        term,
        balance,
        textCell(formatDate(credit.issue_date), "text-body-secondary", "Otorgado"),
        actions,
    );
    return row;
}

// Installments paid out of the term, with a bar; other statuses than "active" also show a badge
export function buildProgress(credit) {
    const { installments_paid: paid } = credit.standing;
    const status = creditStatus(credit);
    const wrapper = document.createElement("div");
    wrapper.className = `term-progress is-${status}`;

    const label = document.createElement("span");
    label.className = "term-progress-label";
    if (status === "completed") {
        label.append(buildStatusBadge(status), ` ${formatMonths(credit.term_months)}`);
    } else if (status === "active") {
        label.textContent = `${paid} de ${credit.term_months} cuotas`;
    } else {
        label.append(buildStatusBadge(status), ` ${paid} de ${credit.term_months}`);
    }

    const bar = document.createElement("span");
    bar.className = "term-progress-bar";
    bar.setAttribute("role", "progressbar");
    bar.setAttribute("aria-valuemin", "0");
    bar.setAttribute("aria-valuemax", String(credit.term_months));
    bar.setAttribute("aria-valuenow", String(paid));
    bar.setAttribute("aria-label", `${paid} de ${credit.term_months} cuotas pagadas`);
    const fill = document.createElement("span");
    fill.style.width = `${(paid / credit.term_months) * 100}%`;
    bar.appendChild(fill);

    wrapper.append(label, bar);
    return wrapper;
}

// Placeholder rows shown while a page loads
export function buildSkeletonRows(count) {
    return Array.from({ length: count }, () => {
        const row = document.createElement("tr");
        row.className = "skeleton-row";
        row.setAttribute("aria-hidden", "true");
        for (let i = 0; i < COLUMNS; i++) {
            const cell = document.createElement("td");
            const bar = document.createElement("span");
            bar.className = "skeleton";
            cell.appendChild(bar);
            row.appendChild(cell);
        }
        return row;
    });
}

// data-label is shown as the field name when rows stack as cards
function textCell(text, className, label) {
    const cell = document.createElement("td");
    cell.className = className;
    cell.dataset.label = label;
    cell.textContent = text;
    return cell;
}

function actionButton(action, variant, icon, label, credit) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `btn btn-sm ${variant}`;
    button.dataset.action = action;
    button.dataset.id = credit.id;
    button.dataset.name = credit.client_name;
    button.title = label;
    button.setAttribute("aria-label", label);
    const iconElement = document.createElement("i");
    iconElement.className = `bi ${icon}`;
    iconElement.setAttribute("aria-hidden", "true");
    button.appendChild(iconElement);
    return button;
}
