import { creditsApi } from "../lib/api.js";
import { formatCurrency, formatMonths, formatPercent } from "../lib/format.js";
import { isValidValue } from "../lib/forms.js";

const QUOTE_DELAY_MS = 300;
// Form fields the estimate depends on
export const QUOTE_FIELDS = ["amount", "interest_rate", "term_months"];

// Live estimate of the monthly payment, computed by the API so it matches the schedule exactly
export function createQuotePanel(form) {
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
