import { buildCreditRow, buildSkeletonRows } from "../components/credit-rows.js";
import { creditsApi, userMessage } from "../lib/api.js";
import { archiveCredit, restoreCredit } from "../lib/credit-actions.js";
import { onCreditsChanged } from "../lib/events.js";
import { formatInteger } from "../lib/format.js";
import { notifyError } from "../lib/notify.js";

const PAGE_SIZES = [10, 25, 50, 100];
const PAGE_SIZE_KEY = "credits:perPage";
const SEARCH_DELAY_MS = 300;
const SKELETON_ROWS = 4;
const FILTER_FIELDS = ["issue_date_from", "issue_date_to", "amount_min", "amount_max"];
const EMPTY_STATUS_TEXT = {
    active: "No hay créditos vigentes al corriente.",
    overdue: "Ningún crédito tiene cuotas vencidas sin pagar.",
    completed: "Todavía no hay créditos liquidados.",
    archived: "No hay créditos archivados.",
};

const state = {
    page: 1, perPage: savedPageSize(), clientName: "", status: "", sort: "id", order: "asc", filters: {}, requestId: 0,
};
let elements;

// The page size is a per-browser preference; storage may be unavailable (private windows)
function savedPageSize() {
    try {
        const value = Number(localStorage.getItem(PAGE_SIZE_KEY));
        return PAGE_SIZES.includes(value) ? value : PAGE_SIZES[0];
    } catch (error) {
        return PAGE_SIZES[0];
    }
}

function savePageSize(value) {
    try { localStorage.setItem(PAGE_SIZE_KEY, String(value)); } catch (error) { /* storage unavailable */ }
}

export function initCredits({ onView, onEdit }) {
    elements = {
        body: document.getElementById("credits-body"),
        search: document.getElementById("credit-search"),
        pageInfo: document.getElementById("page-info"),
        prev: document.getElementById("prev-page"),
        next: document.getElementById("next-page"),
        empty: document.getElementById("credits-empty"),
        emptyTitle: document.getElementById("credits-empty-title"),
        emptyText: document.getElementById("credits-empty-text"),
        emptyAction: document.getElementById("credits-empty-action"),
        filtersForm: document.getElementById("filters-form"),
        filtersError: document.getElementById("filters-error"),
        filtersCount: document.getElementById("filters-count"),
        status: document.getElementById("credits-status"),
        statusFilter: document.getElementById("status-filter"),
        pageSize: document.getElementById("page-size"),
        exportLinks: document.querySelectorAll("[data-export]"),
        sortButtons: document.querySelectorAll(".sort-btn"),
    };

    let searchTimer;
    elements.search.addEventListener("input", () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(() => {
            state.clientName = elements.search.value.trim();
            reload();
        }, SEARCH_DELAY_MS);
    });

    elements.sortButtons.forEach(button => button.addEventListener("click", () => toggleSort(button.dataset.sort)));
    elements.filtersForm.addEventListener("submit", event => { event.preventDefault(); applyFilters(); });
    document.getElementById("filters-clear").addEventListener("click", clearFilters);

    elements.statusFilter.addEventListener("change", () => {
        state.status = elements.statusFilter.value;
        reload();
    });
    elements.pageSize.value = String(state.perPage);
    elements.pageSize.addEventListener("change", () => {
        state.perPage = Number(elements.pageSize.value);
        savePageSize(state.perPage);
        reload();
    });

    elements.prev.addEventListener("click", () => { state.page -= 1; loadCredits(); });
    elements.next.addEventListener("click", () => { state.page += 1; loadCredits(); });

    // One listener handles the buttons of every row
    elements.body.addEventListener("click", event => {
        const button = event.target.closest("button[data-action]");
        if (!button) return;
        const id = Number(button.dataset.id);
        if (button.dataset.action === "view") onView(id);
        if (button.dataset.action === "edit") onEdit?.(id);
        if (button.dataset.action === "archive") archiveCredit(id, button.dataset.name);
        if (button.dataset.action === "restore") restoreCredit(id);
    });

    onCreditsChanged(() => loadCredits());
    renderSortState();
    loadCredits();
}

function reload() {
    state.page = 1;
    loadCredits();
}

// Same column: flip the direction. New column: start ascending
function toggleSort(field) {
    state.order = state.sort === field && state.order === "asc" ? "desc" : "asc";
    state.sort = field;
    renderSortState();
    reload();
}

function renderSortState() {
    elements.sortButtons.forEach(button => {
        const active = button.dataset.sort === state.sort;
        button.closest("th").setAttribute("aria-sort", active ? (state.order === "asc" ? "ascending" : "descending") : "none");
    });
}

function applyFilters() {
    const values = Object.fromEntries(FILTER_FIELDS.map(name => [name, elements.filtersForm.elements[name].value.trim()]));
    const error = filtersError(values);
    elements.filtersError.textContent = error;
    if (error) return;

    state.filters = Object.fromEntries(Object.entries(values).filter(([, value]) => value !== ""));
    const count = Object.keys(state.filters).length;
    elements.filtersCount.textContent = count;
    elements.filtersCount.hidden = count === 0;
    reload();
}

function filtersError({ issue_date_from: from, issue_date_to: to, amount_min: min, amount_max: max }) {
    if (from && to && from > to) return "La fecha final debe ser igual o posterior a la inicial.";
    if (min && max && Number(min) > Number(max)) return "El monto máximo debe ser igual o mayor al mínimo.";
    return "";
}

function clearFilters() {
    elements.filtersForm.reset();
    applyFilters();
}

function currentQuery() {
    return { client_name: state.clientName, status: state.status, sort: state.sort, order: state.order, ...state.filters };
}

async function loadCredits() {
    // Ignore responses that arrive after a newer request (fast typing, quick sorting)
    const requestId = ++state.requestId;
    elements.exportLinks.forEach(link => { link.href = creditsApi.exportUrl(currentQuery(), link.dataset.export); });
    renderSkeleton();

    try {
        const { items, meta } = await creditsApi.list({ page: state.page, perPage: state.perPage, ...currentQuery() });
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
        notifyError(userMessage(error), "No se pudieron cargar los créditos");
    }
}

function render(items, meta) {
    elements.body.replaceChildren(...items.map(buildCreditRow));

    const isEmpty = items.length === 0;
    elements.empty.hidden = !isEmpty;
    if (isEmpty) {
        const searched = Boolean(state.clientName) || Object.keys(state.filters).length > 0;
        const filtered = searched || Boolean(state.status);
        elements.emptyTitle.textContent = filtered ? "Sin resultados" : "Aún no hay créditos registrados";
        if (searched) elements.emptyText.textContent = "Ningún crédito coincide con la búsqueda o los filtros.";
        else if (state.status) elements.emptyText.textContent = EMPTY_STATUS_TEXT[state.status];
        else elements.emptyText.textContent = "Registra el primer crédito para verlo aquí.";
        // Not rendered for roles that cannot register credits
        if (elements.emptyAction) elements.emptyAction.hidden = filtered;
    }

    const pages = Math.max(meta.pages, 1);
    const found = meta.total === 1 ? "crédito encontrado" : "créditos encontrados";
    elements.status.textContent = meta.total === 0
        ? "No se encontraron créditos."
        : `${formatInteger(meta.total)} ${found}, página ${meta.page} de ${pages}.`;
    elements.pageInfo.textContent = `Página ${meta.page} de ${pages} · ${formatInteger(meta.total)} créditos`;
    elements.prev.disabled = meta.page <= 1;
    elements.next.disabled = meta.page >= meta.pages;
}

function renderSkeleton() {
    elements.body.replaceChildren(...buildSkeletonRows(SKELETON_ROWS));
}
