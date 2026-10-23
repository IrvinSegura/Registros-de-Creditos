// Hash-based navigation between the views listed in the sidebar
const VIEWS = {
    dashboard: { hash: "#/panel", title: "Panel", eyebrow: "Resumen de la cartera" },
    credits: { hash: "#/creditos", title: "Créditos", eyebrow: "Cartera" },
    register: { hash: "#/nuevo", title: "Nuevo crédito", eyebrow: "Registro" },
};
const DEFAULT_VIEW = "dashboard";
const APP_NAME = "Registro de Créditos";
export const VIEW_SHOWN = "view:shown";

const viewFromHash = () =>
    Object.keys(VIEWS).find(name => VIEWS[name].hash === window.location.hash) ?? DEFAULT_VIEW;

function showView(name, { focus }) {
    const view = VIEWS[name];
    document.querySelectorAll(".app-view").forEach(section => {
        section.hidden = section.dataset.view !== name;
    });
    document.querySelectorAll("[data-view-link]").forEach(link => {
        const active = link.dataset.viewLink === name;
        link.classList.toggle("active", active);
        if (active) link.setAttribute("aria-current", "page");
        else link.removeAttribute("aria-current");
    });

    document.getElementById("view-title").textContent = view.title;
    document.getElementById("view-eyebrow").textContent = view.eyebrow;
    document.getElementById("topbar-new").hidden = name === "register";
    document.title = `${view.title} · ${APP_NAME}`;

    // On small screens the sidebar is an offcanvas; close it after choosing a view
    bootstrap.Offcanvas.getInstance(document.getElementById("app-sidebar"))?.hide();
    window.scrollTo({ top: 0 });
    // Move focus to the new heading so keyboard and screen reader users land on the view
    if (focus) document.getElementById("view-title").focus();

    document.dispatchEvent(new CustomEvent(VIEW_SHOWN, { detail: { view: name } }));
}

export function initRouter() {
    window.addEventListener("hashchange", () => showView(viewFromHash(), { focus: true }));
    showView(viewFromHash(), { focus: false });
}

export const navigate = name => { window.location.hash = VIEWS[name].hash; };
