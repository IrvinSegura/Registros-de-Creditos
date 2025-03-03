// Form submission event listener
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

// Load credits data and render chart
async function cargarCreditos() {
    let response = await fetch("/creditos");
    let data = await response.json();
    
    let labels = data.map(c => c.cliente);
    let montos = data.map(c => c.monto);
    
    let ctx = document.getElementById("grafica").getContext("2d");
    new Chart(ctx, {
        type: "bar",
        data: { labels, datasets: [{ label: "Montos", data: montos, backgroundColor: "blue" }] }
    });
}

cargarCreditos();
