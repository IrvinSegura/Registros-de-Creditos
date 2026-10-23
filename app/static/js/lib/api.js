// Thin client for the REST API: credits, payments, users and the signed-in account
import { redirectToLogin } from "./session.js";

const BASE_URL = "/api/v1/credits";
const USERS_URL = "/api/v1/users";
// Every state-changing request carries the session's CSRF token (see app/security.py)
const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]')?.content ?? "";

export class ApiError extends Error {
    constructor(message, status, fieldErrors = {}) {
        super(message);
        this.status = status;
        this.fieldErrors = fieldErrors;
    }
}

async function request(url, { headers = {}, ...options } = {}) {
    const response = await fetch(url, {
        ...options,
        headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF_TOKEN, ...headers },
    });
    if (response.status === 204) return null;
    if (response.status === 401) {
        // The session expired: sign in again and come back to the same view
        redirectToLogin();
        throw new ApiError("Tu sesión expiró. Inicia sesión de nuevo.", 401);
    }

    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
        // Error payload: {code, status, message, errors: {json|query: {field: [messages]}}}
        const fieldErrors = body?.errors?.json ?? body?.errors?.query ?? {};
        const message = Object.values(fieldErrors).flat()[0] || body?.message || "Ocurrió un error inesperado.";
        throw new ApiError(message, response.status, fieldErrors);
    }
    return body;
}

const send = (method, url, data) => request(url, { method, body: data === undefined ? undefined : JSON.stringify(data) });

// Builds a query string, leaving out empty values
function toQuery(params) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") query.set(key, value);
    });
    const text = query.toString();
    return text ? `?${text}` : "";
}

export const creditsApi = {
    list: ({ page = 1, perPage = 10, ...filters } = {}) => request(`${BASE_URL}${toQuery({ page, per_page: perPage, ...filters })}`),
    get: id => request(`${BASE_URL}/${id}`),
    create: data => send("POST", BASE_URL, data),
    // The version read when the form was opened: the API answers 412 if someone saved the credit since
    update: (id, data, version) => request(`${BASE_URL}/${id}`, {
        method: "PUT", body: JSON.stringify(data), headers: { "If-Match": `"${version}"` },
    }),
    archive: id => send("POST", `${BASE_URL}/${id}/archive`),
    restore: id => send("POST", `${BASE_URL}/${id}/restore`),
    remove: id => send("DELETE", `${BASE_URL}/${id}`),
    summary: (period = {}) => request(`${BASE_URL}/summary${toQuery(period)}`),
    quote: terms => request(`${BASE_URL}/quote${toQuery(terms)}`),
    amortization: id => request(`${BASE_URL}/${id}/amortization`),
    history: id => request(`${BASE_URL}/${id}/history`),
    payments: id => request(`${BASE_URL}/${id}/payments`),
    addPayment: (id, data) => send("POST", `${BASE_URL}/${id}/payments`, data),
    removePayment: (id, paymentId) => send("DELETE", `${BASE_URL}/${id}/payments/${paymentId}`),
    // Files are downloaded by the browser through plain links
    exportUrl: (filters, format = "csv") => `${BASE_URL}/export${toQuery({ ...filters, format })}`,
    statementUrl: (id, format) => `${BASE_URL}/${id}/statement${toQuery({ format })}`,
};

export const usersApi = {
    list: () => request(USERS_URL),
    create: data => send("POST", USERS_URL, data),
    update: (id, data) => send("PUT", `${USERS_URL}/${id}`, data),
    resetPassword: (id, password) => send("POST", `${USERS_URL}/${id}/password`, { password }),
    endSessions: id => send("POST", `${USERS_URL}/${id}/end-sessions`),
};

export const accountApi = {
    changePassword: data => send("POST", "/api/v1/account/password", data),
};

// Message safe to show to the user: API errors carry Spanish text, network errors do not
export const userMessage = error => (error instanceof ApiError ? error.message : "No se pudo conectar con el servidor.");
