// The signed-in user's own password change, opened from the sidebar
import { accountApi } from "../lib/api.js";
import { clearValidation, handleFormError, setFieldError, validateField, validateForm, withBusyButton } from "../lib/forms.js";
import { notifySuccess } from "../lib/notify.js";

export function initPasswordModal() {
    const modalElement = document.getElementById("password-modal");
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    const form = document.getElementById("password-form");
    const submitButton = form.querySelector("button[type='submit']");
    const fields = form.elements;

    // Both new-password fields must match; checked after the browser rules
    function checkConfirmation() {
        if (!validateField(fields.confirm)) return false;
        const matches = fields.confirm.value === fields.new_password.value;
        setFieldError(fields.confirm, matches ? "" : "Las contraseñas no coinciden.");
        return matches;
    }

    form.addEventListener("input", event => {
        validateField(event.target);
        if (event.target === fields.confirm && fields.confirm.value) checkConfirmation();
    });

    form.addEventListener("submit", async event => {
        event.preventDefault();
        const valid = validateForm(form);
        if (!checkConfirmation() || !valid) return;
        await withBusyButton(submitButton, async () => {
            try {
                await accountApi.changePassword({
                    current_password: fields.current_password.value,
                    new_password: fields.new_password.value,
                });
                modal.hide();
                notifySuccess("Contraseña actualizada");
            } catch (error) {
                handleFormError(form, error);
            }
        });
    });

    modalElement.addEventListener("shown.bs.modal", () => fields.current_password.focus());
    modalElement.addEventListener("hidden.bs.modal", () => {
        form.reset();
        clearValidation(form);
    });

    document.getElementById("account-password").addEventListener("click", () => modal.show());
}
