import { createQuotePanel, QUOTE_FIELDS } from "../components/quote-panel.js";
import { creditsApi } from "../lib/api.js";
import { notifyCreditsChanged } from "../lib/events.js";
import { todayIso } from "../lib/format.js";
import {
    clearValidation, handleFormError, limitIssueDate, readCreditForm, validateField, validateForm, withBusyButton,
} from "../lib/forms.js";
import { notifySuccess } from "../lib/notify.js";

export function initRegisterForm() {
    const form = document.getElementById("credit-form");
    const submitButton = form.querySelector("button[type='submit']");
    const quote = createQuotePanel(form);
    const setDefaultDate = () => {
        limitIssueDate(form);
        form.elements.issue_date.value = todayIso();
    };

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
