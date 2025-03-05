// DOM Content Loaded event listener to validate the form
document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("formulario");
    const inputs = form.querySelectorAll("input");
    
    inputs.forEach(input => {
        input.addEventListener("input", () => validarCampo(input));
    });

    form.addEventListener("submit", async function (e) {
        e.preventDefault();
        let valido = true;
        
        inputs.forEach(input => {
            if (!validarCampo(input)) {
                valido = false;
            }
        });

        if (!valido) return;

        let data = {
            cliente: document.getElementById("cliente").value,
            monto: parseInt(document.getElementById("monto").value),
            tasa_interes: parseFloat(document.getElementById("tasa_interes").value),
            plazo: parseInt(document.getElementById("plazo").value),
            fecha_otorgamiento: document.getElementById("fecha_otorgamiento").value
        };

        let response = await fetch("/creditos", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            mostrarNotificacion("¡Crédito registrado exitosamente!");
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            alert("Error al registrar el crédito.");
        }
    });
});

// Function to show a notification with pop-up message
function mostrarNotificacion(mensaje) {
    const notification = document.createElement("div");
    notification.classList.add("alert", "alert-success", "alert-dismissible", "fade", "show");
    notification.style.position = "fixed";
    notification.style.top = "20px";
    notification.style.right = "20px";
    notification.style.zIndex = "1050";
    notification.setAttribute("role", "alert");
    notification.innerHTML = `
        <strong>${mensaje}</strong>
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.display = "none";
    }, 1000);
}

// Function to validate the form fields
function validarCampo(input) {
    const errorSpan = obtenerErrorSpan(input);
    let valido = true;
    let value = input.value.trim();
    
    if (input.id === "cliente") {
        if (!/^[A-Z][a-zA-Z\s]+$/.test(value)) {
            errorSpan.textContent = "El nombre debe empezar con mayúscula y no contener números.";
            valido = false;
        }
    } else if (input.id === "fecha_otorgamiento") {
        let fechaIngresada = new Date(value);
        let hoy = new Date();
        let year = fechaIngresada.getFullYear();
        let mes = fechaIngresada.getMonth() + 1;
        let dia = fechaIngresada.getDate();
        let esBisiesto = (year % 4 === 0 && year % 100 !== 0) || (year % 400 === 0);
        let diasPorMes = [31, esBisiesto ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
        
        if (isNaN(fechaIngresada) || fechaIngresada < hoy || year < 2000 || year > 2099 || mes > 12 || dia > diasPorMes[mes - 1]) {
            errorSpan.textContent = "Ingrese una fecha válida y no anterior a hoy.";
            valido = false;
        }
    } else if (input.id === "tasa_interes") {
        if (value === "" || isNaN(value) || parseFloat(value) < 1) {
            errorSpan.textContent = "La tasa de interés es obligatoria y debe ser un número mayor o igual a 1.";
            valido = false;
        }
    } else if (input.id === "plazo" || input.id === "monto") {
        if (!/^\d+$/.test(value) || parseInt(value) <= 0) {
            errorSpan.textContent = "Debe ser un número entero positivo.";
            valido = false;
        }
    }
    
    if (valido) {
        errorSpan.textContent = "";
    }
    return valido;
}

// Function to get the error span element
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

// DomContentLoaded event listener to load the credits
document.addEventListener("DOMContentLoaded", function() {
    cargarCreditos();
});

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

// Function to show the edit modal
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

// Event listener for the edit form submission
document.getElementById("formEditarCredito").addEventListener("submit", async function(e) {
    e.preventDefault();

    let id = document.getElementById("edit-id").value;
    let data = {
        cliente: document.getElementById("edit-cliente").value,
        monto: parseFloat(document.getElementById("edit-monto").value),
        tasa_interes: parseFloat(document.getElementById("edit-tasa_interes").value),
        plazo: parseInt(document.getElementById("edit-plazo").value),
        fecha_otorgamiento: document.getElementById("edit-fecha_otorgamiento").value
    };

    let response = await fetch(`/creditos/${id}`, {
        method: "PUT", 
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
    });

    if (response.ok) {
        alert("Crédito actualizado correctamente");
        let modal = bootstrap.Modal.getInstance(document.getElementById("modalEditarCredito"));
        modal.hide();
        cargarCreditos(); 
    } else {
        alert("Error al actualizar el crédito");
    }
}); 

// Function to delete a credit
async function eliminarCredito(id) {
    if (!confirm("¿Seguro que deseas eliminar este crédito?")) return;
    
    let response = await fetch(`/creditos/${id}`, { method: "DELETE" });

    if (response.ok) {
        alert("Crédito eliminado correctamente");
        cargarCreditos(); 
    }
}
