// Sign-in page: password visibility toggle and a busy state while the form is sent
const form = document.getElementById("login-form");
const password = document.getElementById("password");
const toggle = document.getElementById("password-toggle");

toggle.addEventListener("click", () => {
    const visible = password.type === "password";
    password.type = visible ? "text" : "password";
    toggle.setAttribute("aria-pressed", String(visible));
    toggle.setAttribute("aria-label", visible ? "Ocultar contraseña" : "Mostrar contraseña");
    toggle.querySelector("i").className = visible ? "bi bi-eye-slash" : "bi bi-eye";
    password.focus();
});

form.addEventListener("submit", event => {
    const missing = [...form.elements].find(element => element.required && !element.value.trim());
    if (missing) {
        event.preventDefault();
        missing.classList.add("is-invalid");
        missing.focus();
        return;
    }
    const button = form.querySelector("button[type='submit']");
    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Ingresando…';
});

form.addEventListener("input", event => event.target.classList.remove("is-invalid"));
