// Issue-date period filter: quick presets plus a custom range in a dropdown.
// Bootstrap (with its dropdowns) is loaded globally from the CDN in app.html.
import { formatDate, todayIso } from "../lib/format.js";

const MIN_DATE = "2000-01-01";
const ALL = "all";
const CUSTOM = "custom";

// Each preset returns the issue-date range sent to the API
const PRESETS = {
    [ALL]: () => ({}),
    month: () => {
        const today = todayIso();
        return { issue_date_from: `${today.slice(0, 8)}01`, issue_date_to: today };
    },
    year: () => {
        const today = todayIso();
        return { issue_date_from: `${today.slice(0, 4)}-01-01`, issue_date_to: today };
    },
    last12: () => {
        const today = todayIso();
        const [year, month] = today.split("-").map(Number);
        // From the first day of the month 11 months ago, so 12 calendar months are covered
        const start = new Date(Date.UTC(year, month - 12, 1)).toISOString().slice(0, 10);
        return { issue_date_from: start, issue_date_to: today };
    },
};

export function createPeriodPicker({ onChange }) {
    const element = id => document.getElementById(id);
    const options = document.querySelectorAll(".period-presets [data-period]");
    const toggle = element("period-custom-toggle");
    const dropdown = bootstrap.Dropdown.getOrCreateInstance(toggle);
    const form = element("period-form");
    const from = element("period-from");
    const to = element("period-to");
    const error = element("period-error");
    const label = element("period-label");
    const clear = element("period-clear");
    let range = {};

    function select(preset, newRange) {
        range = newRange;
        options.forEach(option => {
            const active = option.dataset.period === preset;
            option.classList.toggle("is-active", active);
            option.setAttribute("aria-pressed", String(active));
        });
        label.textContent = describe(range);
        clear.hidden = preset === ALL;
        onChange(range);
    }

    function showError(message, input) {
        error.textContent = message;
        [from, to].forEach(field => field.classList.toggle("is-invalid", field === input));
        input?.focus();
    }

    options.forEach(option => {
        if (option.dataset.period === CUSTOM) return;
        option.addEventListener("click", () => select(option.dataset.period, PRESETS[option.dataset.period]()));
    });

    // Opens with the range in use, or with this month as a starting point
    toggle.addEventListener("show.bs.dropdown", () => {
        const start = range.issue_date_from ? range : PRESETS.month();
        from.value = start.issue_date_from;
        to.value = start.issue_date_to;
        from.max = to.max = todayIso();
        to.min = from.value || MIN_DATE;
        showError("", null);
    });
    toggle.addEventListener("shown.bs.dropdown", () => from.focus());

    from.addEventListener("change", () => { to.min = from.value || MIN_DATE; });
    form.addEventListener("input", () => showError("", null));
    element("period-cancel").addEventListener("click", () => {
        dropdown.hide();
        toggle.focus();
    });

    form.addEventListener("submit", event => {
        event.preventDefault();
        const today = todayIso();
        if (!from.value) return showError("Elige la fecha inicial.", from);
        if (!to.value) return showError("Elige la fecha final.", to);
        if (from.value > to.value) return showError("La fecha final debe ser igual o posterior a la inicial.", to);
        if (to.value > today) return showError("Las fechas no pueden ser posteriores a hoy.", to);
        select(CUSTOM, { issue_date_from: from.value, issue_date_to: to.value });
        dropdown.hide();
        toggle.focus();
    });

    clear.addEventListener("click", () => {
        select(ALL, {});
        options[0].focus();
    });

    label.textContent = describe(range);
}

function describe({ issue_date_from: start, issue_date_to: end }) {
    if (!start) return "Todo el historial";
    return start === end ? formatDate(start) : `${formatDate(start)} – ${formatDate(end)}`;
}
