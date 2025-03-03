// Event listener for the form submission
document.getElementById("formulario").addEventListener("submit", async function(e) {
    e.preventDefault();
    let data = {
        cliente: document.getElementById("cliente").value,
        monto: parseFloat(document.getElementById("monto").value),
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
        alert("Crédito registrado");
        window.location.reload();
    }
});

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
