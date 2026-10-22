import { creditsApi, userMessage } from "../api.js";
import { notifyCreditsChanged, onCreditsChanged } from "../events.js";
import { formatCurrency, formatDate, formatInteger, formatMonths, formatPercent, initials } from "../format.js";
import { confirmDanger, notifyError, notifySuccess } from "../notify.js";

const PER_PAGE = 10;
const SEARCH_DELAY_MS = 300;
const SKELETON_ROWS = 4;

const state = { page: 1, clientName: "", requestId: 0 };
let elements;

export function initCreditTable({ onEdit }) {
    elements = {
        body: document.getElementById("credits-body"),
        total: document.getElementById("credits-total"),
        search: document.getElementById("credit-search"),
        pageInfo: document.getElementById("page-info"),
        prev: document.getElementById("prev-page"),
        next: document.getElementById("next-page"),
        empty: document.getElementById("credits-empty"),
        emptyTitle: document.getElementById("credits-empty-title"),
        emptyText: document.getElementById("credits-empty-text"),
        emptyAction: document.getElementById("credits-empty-action"),
    };

    let searchTimer;
    elements.search.addEventListener("input", () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            state.clientName = elements.search.value.trim();
            state.page = 1;
            loadCredits();
        }, SEARCH_DELAY_MS);
    });

    elements.prev.addEventListener("click", () => { state.page -= 1; loadCredits(); });
    elements.next.addEventListener("click", () => { state.page += 1; loadCredits(); });
    elements.emptyAction.addEventListener("click", () => {
        bootstrap.Tab.getOrCreateInstance(document.getElementById("register-tab")).show();
    });

    // One listener handles the buttons of every row
    elements.body.addEventListener("click", event => {
        const button = event.target.closest("button[data-action]");
        if (!button) return;
        const id = Number(button.dataset.id);
        if (button.dataset.action === "edit") onEdit(id);
        if (button.dataset.action === "delete") deleteCredit(id, button.dataset.name);
    });

    onCreditsChanged(() => loadCredits());
    loadCredits();
}

async function loadCredits() {
    // Ignore responses that arrive after a newer request (fast typing in the search box)
    const requestId = ++state.requestId;
    renderSkeleton();

    try {
        const { items, meta } = await creditsApi.list({ page: state.page, perPage: PER_PAGE, clientName: state.clientName });
        if (requestId !== state.requestId) return;

        // After deleting the last credit of a page, go back to the previous one
        if (items.length === 0 && meta.page > 1) {
            state.page = meta.page - 1;
            return loadCredits();
        }
        state.page = meta.page;
        render(items, meta);
    } catch (error) {
        if (requestId !== state.requestId) return;
        elements.body.replaceChildren();
        notifyError("No se pudieron cargar los créditos. Intenta de nuevo.");
    }
}

function render(items, meta) {
    elements.body.replaceChildren(...items.map(buildRow));
    elements.total.textContent = formatInteger(meta.total);

    const isEmpty = items.length === 0;
    elements.empty.classList.toggle("d-none", !isEmpty);
    if (isEmpty) {
        const filtered = Boolean(state.clientName);
        elements.emptyTitle.textContent = filtered ? "Sin resultados" : "Aún no hay créditos registrados";
        elements.emptyText.textContent = filtered
            ? `No encontramos créditos para “${state.clientName}”.`
            : "Registra el primer crédito para verlo aquí.";
        elements.emptyAction.classList.toggle("d-none", filtered);
    }

    const pages = Math.max(meta.pages, 1);
    elements.pageInfo.textContent = `Página ${meta.page} de ${pages} · ${formatInteger(meta.total)} créditos`;
    elements.prev.disabled = meta.page <= 1;
    elements.next.disabled = meta.page >= meta.pages;
}

function renderSkeleton() {
    const rows = Array.from({ length: SKELETON_ROWS }, () => {
        const row = document.createElement("tr");
        row.setAttribute("aria-hidden", "true");
        for (let i = 0; i < 6; i++) {
            const cell = document.createElement("td");
            const bar = document.createElement("span");
            bar.className = "skeleton";
            cell.appendChild(bar);
            row.appendChild(cell);
        }
        return row;
    });
    elements.body.replaceChildren(...rows);
}

// Builds a row with textContent so user data is never parsed as HTML
function buildRow(credit) {
    const row = document.createElement("tr");

    const client = document.createElement("td");
    client.dataset.label = "Cliente";
    const clientCell = document.createElement("div");
    clientCell.className = "client-cell";
    const avatar = document.createElement("span");
    avatar.className = "avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = initials(credit.client_name);
    const name = document.createElement("span");
    name.textContent = credit.client_name;
    clientCell.append(avatar, name);
    client.appendChild(clientCell);

    const term = document.createElement("td");
    term.className = "text-end";
    term.dataset.label = "Plazo";
    const termBadge = document.createElement("span");
    termBadge.className = "badge rounded-pill term-badge";
    termBadge.textContent = formatMonths(credit.term_months);
    term.appendChild(termBadge);

    const actions = document.createElement("td");
    actions.className = "text-end row-actions-cell";
    const actionGroup = document.createElement("div");
    actionGroup.className = "row-actions";
    actionGroup.append(
        actionButton("edit", "btn-outline-primary", "bi-pencil", `Editar crédito de ${credit.client_name}`, credit),
        actionButton("delete", "btn-outline-danger", "bi-trash3", `Eliminar crédito de ${credit.client_name}`, credit),
    );
    actions.appendChild(actionGroup);

    row.append(
        client,
        textCell(formatCurrency(credit.amount), "text-end numeric fw-semibold", "Monto"),
        textCell(formatPercent(credit.interest_rate), "text-end numeric", "Tasa"),
        term,
        textCell(formatDate(credit.issue_date), "text-body-secondary", "Otorgado"),
        actions,
    );
    return row;
}

// data-label is shown as the field name when rows stack on small screens
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

async function deleteCredit(id, clientName) {
    const confirmed = await confirmDanger({
        title: "¿Eliminar este crédito?",
        text: `Se eliminará el crédito de ${clientName}. Esta acción no se puede deshacer.`,
        confirmText: "Sí, eliminar",
    });
    if (!confirmed) return;

    try {
        await creditsApi.remove(id);
        notifySuccess("Crédito eliminado");
        notifyCreditsChanged();
    } catch (error) {
        notifyError(userMessage(error));
    }
}
