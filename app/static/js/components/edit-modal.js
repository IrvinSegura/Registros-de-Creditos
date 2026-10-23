import { creditsApi, userMessage } from "../lib/api.js";
import { notifyCreditsChanged } from "../lib/events.js";
import { formatDate } from "../lib/format.js";
import {
    clearValidation, fillCreditForm, handleFormError, readCreditForm, validateField, validateForm, withBusyButton,
} from "../lib/forms.js";
import { notifyError, notifySuccess } from "../lib/notify.js";

export function initEditModal() {
    const modalElement = document.getElementById("edit-credit-modal");
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    const form = document.getElementById("edit-credit-form");
    const submitButton = form.querySelector("button[type='submit']");
    const subtitle = document.getElementById("edit-credit-subtitle");
    let creditId = null;
    let initialValues = "";

    const snapshot = () => JSON.stringify(readCreditForm(form));

    // Saving is only possible once something actually changed
    form.addEventListener("input", event => {
        validateField(event.target);
        submitButton.disabled = snapshot() === initialValues;
    });

    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (!validateForm(form)) return;

        await withBusyButton(submitButton, async () => {
            try {
                await creditsApi.update(creditId, readCreditForm(form));
                modal.hide();
                notifySuccess("Crédito actualizado");
                notifyCreditsChanged();
            } catch (error) {
                handleFormError(form, error);
            }
        });
        submitButton.disabled = snapshot() === initialValues;
    });

    modalElement.addEventListener("shown.bs.modal", () => form.elements.client_name.focus());
    modalElement.addEventListener("hidden.bs.modal", () => clearValidation(form));

    return {
        async open(id) {
            try {
                const credit = await creditsApi.get(id);
                creditId = credit.id;
                fillCreditForm(form, credit);
                clearValidation(form);
                initialValues = snapshot();
                submitButton.disabled = true;
                subtitle.textContent = `${credit.client_name} · otorgado el ${formatDate(credit.issue_date)}`;
                modal.show();
            } catch (error) {
                notifyError(userMessage(error), "No se pudo abrir el crédito");
            }
        },
    };
}
