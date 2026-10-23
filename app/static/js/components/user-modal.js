// One modal for creating and editing accounts
import { usersApi } from "../lib/api.js";
import { clearValidation, handleFormError, validateField, validateForm, withBusyButton } from "../lib/forms.js";
import { notifySuccess } from "../lib/notify.js";

export function initUserModal() {
    const modalElement = document.getElementById("user-modal");
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    const form = document.getElementById("user-form");
    const title = document.getElementById("user-modal-title");
    const submitButton = form.querySelector("button[type='submit']");
    let editing = null;
    let onSaved = () => {};

    // Fields of the other mode are hidden and disabled, so they are neither validated nor sent
    function setMode(mode) {
        form.querySelectorAll("[data-only]").forEach(group => {
            const active = group.dataset.only === mode;
            group.hidden = !active;
            group.querySelectorAll("input").forEach(input => { input.disabled = !active; });
        });
    }

    form.addEventListener("input", event => validateField(event.target));

    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (!validateForm(form)) return;
        const fields = form.elements;
        await withBusyButton(submitButton, async () => {
            try {
                if (editing) {
                    await usersApi.update(editing.id, {
                        full_name: fields.full_name.value.trim(),
                        role: fields.role.value,
                        is_active: fields.is_active.checked,
                    });
                } else {
                    await usersApi.create({
                        username: fields.username.value.trim().toLowerCase(),
                        full_name: fields.full_name.value.trim(),
                        role: fields.role.value,
                        password: fields.password.value,
                    });
                }
                modal.hide();
                notifySuccess(editing ? "Usuario actualizado" : "Usuario creado");
                onSaved();
            } catch (error) {
                handleFormError(form, error);
            }
        });
    });

    modalElement.addEventListener("shown.bs.modal", () => (editing ? form.elements.full_name : form.elements.username).focus());
    modalElement.addEventListener("hidden.bs.modal", () => clearValidation(form));

    return {
        // user is null to create one; onSaved reloads the list
        open(user, saved) {
            editing = user;
            onSaved = saved;
            form.reset();
            clearValidation(form);
            setMode(user ? "edit" : "create");
            title.textContent = user ? `Editar a ${user.full_name}` : "Nuevo usuario";
            if (user) {
                form.elements.full_name.value = user.full_name;
                form.elements.role.value = user.role;
                form.elements.is_active.checked = user.is_active;
            }
            modal.show();
        },
    };
}
