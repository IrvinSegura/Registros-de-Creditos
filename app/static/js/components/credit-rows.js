// Rows of the credits table, built with textContent so user data is never parsed as HTML
import { formatCurrency, formatDate, formatMonths, formatPercent, initials } from "../lib/format.js";
import { can, PERMISSIONS } from "../lib/session.js";

const COLUMNS = 6;

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
    term.className = "text-end";
    term.dataset.label = "Plazo";
    const termBadge = document.createElement("span");
    termBadge.className = "badge rounded-pill term-badge";
    termBadge.textContent = formatMonths(credit.term_months);
    term.appendChild(termBadge);

    const actions = document.createElement("td");
    actions.className = "text-end cell-actions";
    const actionGroup = document.createElement("div");
    actionGroup.className = "row-actions";
    actionGroup.append(
        actionButton("view", "btn-outline-secondary", "bi-eye", `Ver detalle del crédito de ${credit.client_name}`, credit),
    );
    if (can(PERMISSIONS.update)) {
        actionGroup.append(
            actionButton("edit", "btn-outline-primary", "bi-pencil", `Editar crédito de ${credit.client_name}`, credit),
        );
    }
    if (can(PERMISSIONS.delete)) {
        actionGroup.append(
            actionButton("delete", "btn-outline-danger", "bi-trash3", `Eliminar crédito de ${credit.client_name}`, credit),
        );
    }
    actions.appendChild(actionGroup);

    row.append(
        client,
        textCell(formatCurrency(credit.amount), "text-end numeric fw-semibold", "Monto"),
        textCell(formatPercent(credit.interest_rate), "text-end numeric", "Tasa anual"),
        term,
        textCell(formatDate(credit.issue_date), "text-body-secondary", "Otorgado"),
        actions,
    );
    return row;
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
