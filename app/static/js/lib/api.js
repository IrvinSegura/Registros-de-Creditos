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
    create: data => request(BASE_URL, { method: "POST", body: JSON.stringify(data) }),
    update: (id, data) => request(`${BASE_URL}/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    remove: id => request(`${BASE_URL}/${id}`, { method: "DELETE" }),
    summary: (period = {}) => request(`${BASE_URL}/summary${toQuery(period)}`),
    quote: terms => request(`${BASE_URL}/quote${toQuery(terms)}`),
    amortization: id => request(`${BASE_URL}/${id}/amortization`),
    history: id => request(`${BASE_URL}/${id}/history`),
    // The CSV is downloaded by the browser through a plain link
    exportUrl: filters => `${BASE_URL}/export${toQuery(filters)}`,
};

// Message safe to show to the user: API errors carry Spanish text, network errors do not
export const userMessage = error => (error instanceof ApiError ? error.message : "No se pudo conectar con el servidor.");
