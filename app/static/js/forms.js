import { userMessage } from "./api.js";
import { notifyError } from "./notify.js";

// Same rules as the API; messages are shown to the user, so they stay in Spanish
const VALIDATORS = {
    client_name: value => /^[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]{2,99}$/.test(value)
        || "Debe empezar con mayúscula y contener solo letras y espacios (3 a 100 caracteres).",
    issue_date: value => (/^\d{4}-\d{2}-\d{2}$/.test(value) && value >= "2000-01-01")
        || "Ingresa una fecha válida posterior al 01/01/2000.",
    amount: value => (value !== "" && Number(value) > 0 && Number(value) < 1e12)
        || "El monto debe ser mayor a 0.",
    interest_rate: value => (value !== "" && Number(value) > 0 && Number(value) <= 100)
        || "La tasa debe ser mayor a 0 y como máximo 100.",
    term_months: value => (/^\d+$/.test(value) && Number(value) >= 1 && Number(value) <= 360)
        || "El plazo debe ser un número entero entre 1 y 360 meses.",
};

const validatedFields = form => [...form.elements].filter(element => element.name in VALIDATORS);

function setFieldError(input, message) {
    input.classList.toggle("is-invalid", Boolean(message));
    const feedback = document.getElementById(`${input.id}-error`);
    if (feedback) feedback.textContent = message;
}

// True when a raw value passes the rule of its field (used without touching the form UI)
export function isValidValue(name, value) {
    return VALIDATORS[name]?.(String(value).trim()) === true;
}

export function validateField(input) {
    if (!(input.name in VALIDATORS)) return true;
    const result = VALIDATORS[input.name](input.value.trim());
    setFieldError(input, typeof result === "string" ? result : "");
    return typeof result !== "string";
}

// Validates every field so all errors are shown at once
export function validateForm(form) {
    return validatedFields(form).map(validateField).every(Boolean);
}

export function clearValidation(form) {
    validatedFields(form).forEach(input => setFieldError(input, ""));
}

export function readCreditForm(form) {
    const value = name => form.elements[name].value.trim();
    return {
        client_name: value("client_name"),
        // Decimals travel as strings so the API stores them without float rounding
        amount: value("amount"),
        interest_rate: value("interest_rate"),
        term_months: Number.parseInt(value("term_months"), 10),
        issue_date: value("issue_date"),
    };
}

export function fillCreditForm(form, credit) {
    validatedFields(form).forEach(input => { input.value = credit[input.name] ?? ""; });
}

// Shows API validation errors next to their fields, or a dialog for anything else
export function handleFormError(form, error) {
    const entries = Object.entries(error.fieldErrors ?? {}).filter(([name]) => form.elements[name]);
    if (entries.length === 0) {
        notifyError(userMessage(error));
        return;
    }
    entries.forEach(([name, messages]) => setFieldError(form.elements[name], messages[0]));
    form.elements[entries[0][0]].focus();
}

// Disables the button and shows a spinner while the action runs
export async function withBusyButton(button, action) {
    const content = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Guardando…';
    try {
        return await action();
    } finally {
        button.innerHTML = content;
        button.disabled = false;
    }
}
