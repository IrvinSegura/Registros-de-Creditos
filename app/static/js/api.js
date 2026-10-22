// Thin client for the credits REST API
const BASE_URL = "/api/v1/credits";

export class ApiError extends Error {
    constructor(message, status, fieldErrors = {}) {
        super(message);
        this.status = status;
        this.fieldErrors = fieldErrors;
    }
}

async function request(url, options = {}) {
    const response = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options });
    if (response.status === 204) return null;

    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
        // Error payload: {code, status, message, errors: {json|query: {field: [messages]}}}
        const fieldErrors = body?.errors?.json ?? body?.errors?.query ?? {};
        const message = Object.values(fieldErrors).flat()[0] || body?.message || "Ocurrió un error inesperado.";
        throw new ApiError(message, response.status, fieldErrors);
    }
    return body;
}

export const creditsApi = {
    list({ page = 1, perPage = 10, clientName = "" } = {}) {
        const params = new URLSearchParams({ page, per_page: perPage });
        if (clientName) params.set("client_name", clientName);
        return request(`${BASE_URL}?${params}`);
    },
    get: id => request(`${BASE_URL}/${id}`),
    create: data => request(BASE_URL, { method: "POST", body: JSON.stringify(data) }),
    update: (id, data) => request(`${BASE_URL}/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    remove: id => request(`${BASE_URL}/${id}`, { method: "DELETE" }),
    summary: () => request(`${BASE_URL}/summary`),
};

// Message safe to show to the user: API errors carry Spanish text, network errors do not
export const userMessage = error => (error instanceof ApiError ? error.message : "No se pudo conectar con el servidor.");
