// DOM elements for the diferents 
document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("formulario");
    const formEditar = document.getElementById("formEditarCredito");
    const inputs = form.querySelectorAll("input");
    const inputsEditar = formEditar.querySelectorAll("input");
    const submitButtonEditar = formEditar.querySelector("button[type='submit']");
    const initialValuesEditar = {};

    // Event listener for the inputs
    inputs.forEach(input => input.addEventListener("input", () => validarCampo(input)));
    inputsEditar.forEach(input => {
        initialValuesEditar[input.id] = input.value.trim();
        input.addEventListener("input", () => validarCampo(input));
    });

    // Event listener for the form submit
    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        if (![...inputs].every(validarCampo)) return;
        await enviarDatos("POST", "/creditos", obtenerDatosFormulario());
        actualizarGrafico(); 
    });

    // Event listener for the button edit
    formEditar.addEventListener("input", () => {
        submitButtonEditar.disabled = ![...inputsEditar].some(input => input.value.trim() !== initialValuesEditar[input.id]);
    });

    // Event send data to the endpoint
    formEditar.addEventListener("submit", async function (e) {
        e.preventDefault();
        if (![...inputsEditar].every(validarCampo)) return;
        let id = document.getElementById("edit-id").value;
        await enviarDatos("PUT", `/creditos/${id}`, obtenerDatosFormulario(true));
        actualizarGrafico();
    });

    cargarCreditos(); 
    cargarCreditosParaGrafica(); 
});

// Validations in the inputs
const validaciones = {
    "cliente": value => /^[A-Z][a-zA-Z\s]+$/.test(value) || "El nombre debe empezar con mayúscula y no contener números.",
    "edit-cliente": value => validaciones["cliente"](value),
    "fecha_otorgamiento": value => {
        let fecha = new Date(value), hoy = new Date();
        hoy.setHours(0, 0, 0, 0);
        return !isNaN(fecha.getTime()) && fecha >= hoy || "Ingrese una fecha válida y no anterior a hoy.";
    },
    "edit-fecha_otorgamiento": value => validaciones["fecha_otorgamiento"](value),
    "tasa_interes": value => {
        let tasa = parseFloat(value);
        return isFinite(tasa) && tasa >= 1 && tasa <= 100 || "La tasa debe ser un número entre 1 y 100.";
    },
    "edit-tasa_interes": value => validaciones["tasa_interes"](value),
    "plazo": value => {
        let plazo = parseInt(value);
        return isFinite(plazo) && plazo > 0 && plazo <= 360 || "El plazo debe ser mayor a 0 y menor o igual a 360.";
    },
    "edit-plazo": value => validaciones["plazo"](value),
    "monto": value => {
        let monto = parseInt(value);
        return isFinite(monto) && monto > 0 || "El monto debe ser un número mayor a 0.";
    },
    "edit-monto": value => validaciones["monto"](value)
};

// Function to validate the inputs
function validarCampo(input) {
    let errorSpan = obtenerErrorSpan(input);
    let resultado = validaciones[input.id]?.(input.value.trim());
    errorSpan.textContent = typeof resultado === "string" ? resultado : "";
    return typeof resultado !== "string";
}

// Function to get the error span
function obtenerErrorSpan(input) {
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
function obtenerDatosFormulario(edit = false) {
    return {
        cliente: document.getElementById(`${edit ? "edit-" : ""}cliente`).value,
        monto: parseFloat(document.getElementById(`${edit ? "edit-" : ""}monto`).value),
        tasa_interes: parseFloat(document.getElementById(`${edit ? "edit-" : ""}tasa_interes`).value),
        plazo: parseInt(document.getElementById(`${edit ? "edit-" : ""}plazo`).value),
        fecha_otorgamiento: document.getElementById(`${edit ? "edit-" : ""}fecha_otorgamiento`).value
    };
}

// Function to send the data to the endpoint
async function enviarDatos(method, url, data) {
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
            cargarCreditos(); 
            actualizarGrafico(); 
            document.getElementById("formulario").reset();

            let modalEditar = bootstrap.Modal.getInstance(document.getElementById("modalEditarCredito"));
            if (modalEditar) {
                modalEditar.hide();
            }
        });
    } else {
        let data = await response.json();
        let errorMsg = data?.cliente || data?.monto || data?.tasa_interes || data?.plazo || data?.fecha_otorgamiento || "Error desconocido";
        Swal.fire({
            icon: "error",
            title: "Error",
            text: errorMsg,
        });
    }
}

// Function to load the credits
async function cargarCreditos() {
    let response = await fetch("/creditos");
    let data = await response.json();
    let tbody = document.getElementById("creditos-body");
    tbody.innerHTML = ""; 

    data.forEach(credito => {
        let row = document.createElement("tr");
        row.innerHTML = `
            <td>${credito.cliente}</td>
            <td>${credito.monto}</td>
            <td>${credito.tasa_interes}%</td>
            <td>${credito.plazo}</td>
            <td>${credito.fecha_otorgamiento}</td>
            <td>
                <button class="btn btn-warning btn-sm me-2" onclick="mostrarModalEditar(${credito.id})">✏️ Editar</button>
                <button class="btn btn-danger btn-sm" onclick="eliminarCredito(${credito.id})">🗑️ Eliminar</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Function to show the modal to edit a credit
async function mostrarModalEditar(id) {
    let response = await fetch(`/creditos/${id}`, { method: "GET" });
    if (!response.ok) {
        alert("Error al obtener los datos del crédito.");
        return;
    }
    let credito = await response.json();

    document.getElementById("edit-id").value = credito.id;
    document.getElementById("edit-cliente").value = credito.cliente;
    document.getElementById("edit-monto").value = credito.monto;
    document.getElementById("edit-tasa_interes").value = credito.tasa_interes;
    document.getElementById("edit-plazo").value = credito.plazo;
    document.getElementById("edit-fecha_otorgamiento").value = credito.fecha_otorgamiento;

    let modal = new bootstrap.Modal(document.getElementById("modalEditarCredito"));
    modal.show();
}

// Function to delete a credit
async function eliminarCredito(id) {
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
            let response = await fetch(`/creditos/${id}`, { method: "DELETE" });

            if (response.ok) {
                Swal.fire("Eliminado", "El crédito ha sido eliminado correctamente.", "success");
                cargarCreditos();
                actualizarGrafico(); 
            } else {
                Swal.fire("Error", "No se pudo eliminar el crédito.", "error");
            }
        }
    });
}

// Function to load the credits for the graph
async function cargarCreditosParaGrafica() {
    let response = await fetch("/creditos");
    let data = await response.json();
    const clientes = data.map(credito => credito.cliente);
    const montos = data.map(credito => credito.monto);


    const ctx = document.getElementById('creditosChart').getContext('2d');
    creditosChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: clientes,
            datasets: [{
                label: 'Montos de créditos',
                data: montos,
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                borderColor: 'rgba(54, 162, 235, 1)',
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

// Function to update the graph
async function actualizarGrafico() {
    let response = await fetch("/creditos"); 
    let data = await response.json();

    const clientes = data.map(credito => credito.cliente);
    const montos = data.map(credito => credito.monto);

    creditosChart.data.labels = clientes;
    creditosChart.data.datasets[0].data = montos;

    creditosChart.update();
}
