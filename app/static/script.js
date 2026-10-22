// REST API endpoint and table pagination state
const CREDITS_API = "/api/v1/credits";
const CREDITS_PER_PAGE = 10;
// The API caps per_page at 100, so the chart shows up to the first 100 credits
const CHART_CREDITS_LIMIT = 100;
// Form inputs use the API field names as ids; the edit form prefixes them with "edit-"
const CREDIT_FIELDS = ["client_name", "amount", "interest_rate", "term_months", "issue_date"];
let currentPage = 1;
let creditsChart;

// DOM elements for the different forms
document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("credit-form");
    const editForm = document.getElementById("edit-credit-form");
    const inputs = form.querySelectorAll("input");
    const editInputs = editForm.querySelectorAll("input");
    const editSubmitButton = editForm.querySelector("button[type='submit']");
    const initialEditValues = {};

    // Event listener for the inputs
    inputs.forEach(input => input.addEventListener("input", () => validateField(input)));
    editInputs.forEach(input => {
        initialEditValues[input.id] = input.value.trim();
        input.addEventListener("input", () => validateField(input));
    });

    // Event listener for the form submit
    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        if (![...inputs].every(validateField)) return;
        await sendCredit("POST", CREDITS_API, getFormData());
        updateChart();
    });

    // Event listener for the button edit
    editForm.addEventListener("input", () => {
        editSubmitButton.disabled = ![...editInputs].some(input => input.value.trim() !== initialEditValues[input.id]);
    });

    // Event send data to the endpoint
    editForm.addEventListener("submit", async function (e) {
        e.preventDefault();
        if (![...editInputs].every(validateField)) return;
        let id = document.getElementById("edit-id").value;
        await sendCredit("PUT", `${CREDITS_API}/${id}`, getFormData(true));
        updateChart();
    });

    // Pagination buttons
    document.getElementById("prev-page").addEventListener("click", () => loadCredits(currentPage - 1));
    document.getElementById("next-page").addEventListener("click", () => loadCredits(currentPage + 1));

    loadCredits();
    loadChart();
});

// Validations in the inputs; messages are shown to the user, so they stay in Spanish
const validators = {
    // Same rule as the API: accents and ñ allowed, 3 to 100 characters
    "client_name": value => /^[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]{2,99}$/.test(value) || "El nombre debe empezar con mayúscula y contener solo letras y espacios (3 a 100 caracteres).",
    // Same rule as the API; ISO strings compare without timezone shifts
    "issue_date": value => /^\d{4}-\d{2}-\d{2}$/.test(value) && value >= "2000-01-01" || "Ingrese una fecha válida posterior al 01/01/2000.",
    "interest_rate": value => {
        let rate = parseFloat(value);
        return isFinite(rate) && rate >= 1 && rate <= 100 || "La tasa debe ser un número entre 1 y 100.";
    },
    "term_months": value => {
        let term = parseInt(value);
        return isFinite(term) && term > 0 && term <= 360 || "El plazo debe ser mayor a 0 y menor o igual a 360.";
    },
    "amount": value => {
        let amount = parseInt(value);
        return isFinite(amount) && amount > 0 || "El monto debe ser un número mayor a 0.";
    }
};

// Function to validate the inputs
function validateField(input) {
    let errorSpan = getErrorSpan(input);
    let result = validators[input.id.replace(/^edit-/, "")]?.(input.value.trim());
    errorSpan.textContent = typeof result === "string" ? result : "";
    return typeof result !== "string";
}

// Function to get the error span
function getErrorSpan(input) {
    let errorSpan = input.nextElementSibling;
    if (!errorSpan || !errorSpan.classList.contains("error-message")) {
        errorSpan = document.createElement("span");
        errorSpan.classList.add("error-message");
        errorSpan.style.color = "red";
        input.parentNode.appendChild(errorSpan);
    }
    return errorSpan;
}

// Function to get the data from the form
function getFormData(edit = false) {
    let value = field => document.getElementById(`${edit ? "edit-" : ""}${field}`).value;
    return {
        client_name: value("client_name"),
        amount: parseFloat(value("amount")),
        interest_rate: parseFloat(value("interest_rate")),
        term_months: parseInt(value("term_months")),
        issue_date: value("issue_date")
    };
}

// Function to send the data to the endpoint
async function sendCredit(method, url, data) {
    let response = await fetch(url, {
        method: method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        Swal.fire({
            icon: "success",
            title: method === "POST" ? "¡Crédito registrado!" : "¡Crédito actualizado!",
            text: `El crédito ha sido ${method === "POST" ? "registrado" : "actualizado"} exitosamente.`,
            timer: 1500,
            showConfirmButton: false
        }).then(() => {
            loadCredits(currentPage);
            updateChart();
            document.getElementById("credit-form").reset();

            let editModal = bootstrap.Modal.getInstance(document.getElementById("edit-credit-modal"));
            if (editModal) {
                editModal.hide();
            }
        });
    } else {
        let error = await response.json().catch(() => ({}));
        Swal.fire({
            icon: "error",
            title: "Error",
            text: getErrorMessage(error),
        });
    }
}

// Function to get the first readable message from an API error ({code, status, message, errors})
function getErrorMessage(error) {
    let fieldErrors = Object.values(error?.errors?.json ?? {}).flat();
    return fieldErrors[0] || error?.message || "Error desconocido";
}

// Function to load one page of credits
async function loadCredits(page = 1) {
    let response = await fetch(`${CREDITS_API}?page=${page}&per_page=${CREDITS_PER_PAGE}`);
    if (!response.ok) {
        Swal.fire("Error", "No se pudieron cargar los créditos.", "error");
        return;
    }
    let { items, meta } = await response.json();

    // After deleting the last credit of a page, go back to the previous one
    if (items.length === 0 && meta.page > 1) {
        return loadCredits(meta.page - 1);
    }
    currentPage = meta.page;

    document.getElementById("credits-body").replaceChildren(...items.map(buildCreditRow));

    document.getElementById("page-info").textContent = `Página ${meta.page} de ${Math.max(meta.pages, 1)} · ${meta.total} créditos`;
    document.getElementById("prev-page").disabled = meta.page <= 1;
    document.getElementById("next-page").disabled = meta.page >= meta.pages;
}

// Function to build a table row; textContent keeps user data from being parsed as HTML
function buildCreditRow(credit) {
    let row = document.createElement("tr");
    let values = [credit.client_name, credit.amount, `${credit.interest_rate}%`, credit.term_months, credit.issue_date];
    values.forEach(value => {
        let td = document.createElement("td");
        td.textContent = value;
        row.appendChild(td);
    });

    let actions = document.createElement("td");
    let editButton = createButton("btn btn-warning btn-sm me-2", "✏️ Editar", () => showEditModal(credit.id));
    let deleteButton = createButton("btn btn-danger btn-sm", "🗑️ Eliminar", () => deleteCredit(credit.id));
    actions.append(editButton, deleteButton);
    row.appendChild(actions);
    return row;
}

// Function to create a button with its click handler
function createButton(classes, text, onClick) {
    let button = document.createElement("button");
    button.type = "button";
    button.className = classes;
    button.textContent = text;
    button.addEventListener("click", onClick);
    return button;
}

// Function to show the modal to edit a credit
async function showEditModal(id) {
    let response = await fetch(`${CREDITS_API}/${id}`);
    if (!response.ok) {
        alert("Error al obtener los datos del crédito.");
        return;
    }
    let credit = await response.json();

    document.getElementById("edit-id").value = credit.id;
    CREDIT_FIELDS.forEach(field => {
        document.getElementById(`edit-${field}`).value = credit[field];
    });

    let modal = new bootstrap.Modal(document.getElementById("edit-credit-modal"));
    modal.show();
}

// Function to delete a credit
async function deleteCredit(id) {
    Swal.fire({
        title: "¿Está seguro?",
        text: "Esta acción no se puede deshacer.",
        icon: "warning",
        showCancelButton: true,
        confirmButtonColor: "#d33",
        cancelButtonColor: "#3085d6",
        confirmButtonText: "Sí, eliminar",
        cancelButtonText: "Cancelar"
    }).then(async (result) => {
        if (result.isConfirmed) {
            let response = await fetch(`${CREDITS_API}/${id}`, { method: "DELETE" });

            if (response.ok) {
                Swal.fire("Eliminado", "El crédito ha sido eliminado correctamente.", "success");
                loadCredits(currentPage);
                updateChart();
            } else {
                Swal.fire("Error", "No se pudo eliminar el crédito.", "error");
            }
        }
    });
}

// Function to get the client names and amounts shown in the chart
async function getChartData() {
    let response = await fetch(`${CREDITS_API}?per_page=${CHART_CREDITS_LIMIT}`);
    let { items } = await response.json();
    return {
        clientNames: items.map(credit => credit.client_name),
        // Amounts arrive as decimal strings ("1500.00")
        amounts: items.map(credit => Number(credit.amount))
    };
}

// Function to load the credits for the chart
async function loadChart() {
    const { clientNames, amounts } = await getChartData();

    const ctx = document.getElementById("credits-chart").getContext("2d");
    creditsChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: clientNames,
            datasets: [{
                label: "Montos de créditos",
                data: amounts,
                backgroundColor: "rgba(54, 162, 235, 0.2)",
                borderColor: "rgba(54, 162, 235, 1)",
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Function to update the chart
async function updateChart() {
    if (!creditsChart) return;
    const { clientNames, amounts } = await getChartData();

    creditsChart.data.labels = clientNames;
    creditsChart.data.datasets[0].data = amounts;

    creditsChart.update();
}
