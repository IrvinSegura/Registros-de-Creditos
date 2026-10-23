import { userMessage } from "./api.js";
import { todayIso } from "./format.js";
import { notifyError } from "./notify.js";

const MAX_AMOUNT = 999999999999.99;
// Plain decimal with at most two significant places (1.500 is fine, 1.505 is not)
const CENTS = /^\d+(\.\d{0,2}0*)?$/;
const PLACES_MESSAGE = "Usa como máximo 2 decimales.";
// Same rule as the API: words joined by a space, hyphen or apostrophe, each optionally ending in a period
const CLIENT_NAME = /^[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]*\.?(?:[ '-][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+\.?)*$/;

function checkClientName(value) {
    const name = value.replace(/’/g, "'").split(/\s+/).filter(Boolean).join(" ");
    if (name.length < 3 || name.length > 100) return "El nombre debe tener entre 3 y 100 caracteres.";
    return CLIENT_NAME.test(name)
        || "Debe empezar con mayúscula y usar letras, espacios, guion, apóstrofo o punto.";
}

function checkDate(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value) || value < "2000-01-01") return "Ingresa una fecha válida posterior al 01/01/2000.";
    return value <= todayIso() || "La fecha no puede ser posterior a hoy.";
}

// Forms that are not about credits validate their own fields with the browser rules (minlength, required...)
function checkNative(input) {
    if (input.validity.valid) return true;
    if (input.validity.valueMissing) return "Este campo es obligatorio.";
    if (input.validity.tooShort) return `Debe tener al menos ${input.minLength} caracteres.`;
    return input.validationMessage;
}

function checkCents(value, min, max, rangeMessage) {
    if (!/^\d+(\.\d*)?$/.test(value)) return "Debe ser un número válido.";
    if (!CENTS.test(value)) return PLACES_MESSAGE;
    return (Number(value) >= min && Number(value) <= max) || rangeMessage;
}

// Same rules as the API; messages are shown to the user, so they stay in Spanish
const VALIDATORS = {
    client_name: checkClientName,
    issue_date: checkDate,
    amount: value => checkCents(value, 0.01, MAX_AMOUNT, "El monto debe ser mayor a 0 y como máximo 999,999,999,999.99."),
    interest_rate: value => checkCents(value, 0.01, 100, "La tasa debe ser mayor a 0 y como máximo 100."),
    term_months: value => (/^\d+$/.test(value) && Number(value) >= 1 && Number(value) <= 360)
        || "El plazo debe ser un número entero entre 1 y 360 meses.",
    // Payments: the API also checks the issue date and what is left to pay
    paid_on: checkDate,
    note: value => value.length <= 200 || "La nota debe tener como máximo 200 caracteres.",
};

// Fields with a rule above, plus any field of a form marked data-native-validation
const validatedFields = form => [...form.elements].filter(element => element.name in VALIDATORS
    || (form.dataset.nativeValidation !== undefined && element.name && element.willValidate));

export function setFieldError(input, message) {
    input.classList.toggle("is-invalid", Boolean(message));
    const feedback = document.getElementById(`${input.id}-error`);
    if (feedback) feedback.textContent = message;
}

// True when a raw value passes the rule of its field (used without touching the form UI)
export function isValidValue(name, value) {
    return VALIDATORS[name]?.(String(value).trim()) === true;
}

export function validateField(input) {
    let result = true;
    if (input.form?.dataset.nativeValidation !== undefined) result = checkNative(input);
    else if (input.name in VALIDATORS) result = VALIDATORS[input.name](input.value.trim());
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
    limitIssueDate(form);
}

// The date picker cannot go past today, matching the API rule
export function limitIssueDate(form) {
    form.elements.issue_date.max = todayIso();
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
