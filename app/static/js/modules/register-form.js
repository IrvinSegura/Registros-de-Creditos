import { creditsApi } from "../api.js";
import { notifyCreditsChanged } from "../events.js";
import { todayIso } from "../format.js";
import { clearValidation, handleFormError, readCreditForm, validateField, validateForm, withBusyButton } from "../forms.js";
import { notifySuccess } from "../notify.js";

export function initRegisterForm() {
    const form = document.getElementById("credit-form");
    const submitButton = form.querySelector("button[type='submit']");
    const setDefaultDate = () => { form.elements.issue_date.value = todayIso(); };

    form.addEventListener("input", event => validateField(event.target));
    form.addEventListener("reset", () => {
        clearValidation(form);
        // The reset event fires before the fields are cleared
        setTimeout(setDefaultDate);
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
