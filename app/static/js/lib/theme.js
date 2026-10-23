// The initial theme is applied by an inline script in base.html before the first paint
const STORAGE_KEY = "theme";

const currentTheme = () => document.documentElement.getAttribute("data-bs-theme");

function renderToggle(button) {
    const dark = currentTheme() === "dark";
    button.querySelector("i").className = dark ? "bi bi-sun" : "bi bi-moon-stars";
    button.querySelector("span").textContent = dark ? "Tema claro" : "Tema oscuro";
    button.setAttribute("aria-label", dark ? "Cambiar a tema claro" : "Cambiar a tema oscuro");
}

export function initThemeToggle(onChange) {
    const button = document.getElementById("theme-toggle");
    renderToggle(button);

    button.addEventListener("click", () => {
        const next = currentTheme() === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-bs-theme", next);
        try {
            localStorage.setItem(STORAGE_KEY, next);
        } catch (error) {
            // Storage may be blocked; the theme still applies for this visit
        }
        renderToggle(button);
        onChange?.(next);
    });
}
