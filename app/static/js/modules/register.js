import { creditsApi } from "../api.js";
import { notifyCreditsChanged } from "../events.js";
import { formatCurrency, formatMonths, formatPercent, todayIso } from "../format.js";
import {
    clearValidation, handleFormError, isValidValue, readCreditForm, validateField, validateForm, withBusyButton,
} from "../forms.js";
import { notifySuccess } from "../notify.js";

const QUOTE_DELAY_MS = 300;
const QUOTE_FIELDS = ["amount", "interest_rate", "term_months"];

export function initRegisterForm() {
    const form = document.getElementById("credit-form");
    const submitButton = form.querySelector("button[type='submit']");
    const quote = createQuotePanel(form);
    const setDefaultDate = () => { form.elements.issue_date.value = todayIso(); };

    form.addEventListener("input", event => {
        validateField(event.target);
        if (QUOTE_FIELDS.includes(event.target.name)) quote.schedule();
    });
    form.addEventListener("reset", () => {
        clearValidation(form);
        // The reset event fires before the fields are cleared
        setTimeout(() => { setDefaultDate(); quote.schedule(); });
    });

    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (!validateForm(form)) return;

        await withBusyButton(submitButton, async () => {
            try {
                await creditsApi.create(readCreditForm(form));
                form.reset();
                notifySuccess("Crédito registrado");
                notifyCreditsChanged();
            } catch (error) {
                handleFormError(form, error);
            }
        });
    });

    setDefaultDate();
}

// Live estimate of the monthly payment, computed by the API so it matches the schedule exactly
function createQuotePanel(form) {
    const element = id => document.getElementById(id);
    const empty = element("quote-empty");
    const result = element("quote-result");
    let timer;
    let requestId = 0;

    const showEmpty = () => { empty.hidden = false; result.hidden = true; };

    async function update() {
        const terms = Object.fromEntries(QUOTE_FIELDS.map(name => [name, form.elements[name].value.trim()]));
        if (!QUOTE_FIELDS.every(name => isValidValue(name, terms[name]))) {
            requestId++;
            showEmpty();
            return;
        }

        const current = ++requestId;
        try {
            const data = await creditsApi.quote(terms);
            if (current !== requestId) return;
            render(terms, data);
        } catch (error) {
            if (current === requestId) showEmpty();
        }
    }

    function render(terms, data) {
        const principal = Number(terms.amount);
        const total = Number(data.total_paid);
        const principalShare = total > 0 ? (principal / total) * 100 : 100;

        element("quote-payment").textContent = formatCurrency(data.monthly_payment);
        element("quote-terms").textContent =
            `${formatMonths(terms.term_months)} · tasa anual de ${formatPercent(terms.interest_rate)}`;
        element("quote-principal").textContent = formatCurrency(principal);
        element("quote-interest").textContent = formatCurrency(data.total_interest);
        element("quote-total").textContent = formatCurrency(data.total_paid);
        element("quote-split-principal").style.width = `${principalShare}%`;
        element("quote-split-interest").style.width = `${100 - principalShare}%`;
        element("quote-split").setAttribute(
            "aria-label", `Capital ${principalShare.toFixed(0)} %, intereses ${(100 - principalShare).toFixed(0)} %`,
        );
        empty.hidden = true;
        result.hidden = false;
    }

    return {
        schedule() {
            clearTimeout(timer);
            timer = setTimeout(update, QUOTE_DELAY_MS);
        },
    };
}
