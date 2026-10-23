// Accounts list for administrators: create, edit, reset passwords and end sessions
import { usersApi, userMessage } from "../lib/api.js";
import { formatDateTime, initials } from "../lib/format.js";
import { confirmAction, notifyError, notifySuccess, promptNewPassword } from "../lib/notify.js";
import { VIEW_SHOWN } from "../lib/router.js";

const MIN_PASSWORD_LENGTH = 10;

export function initUsers({ userModal }) {
    const body = document.getElementById("users-body");
    let users = [];

    async function load() {
        try {
            users = await usersApi.list();
            body.replaceChildren(...users.map(buildUserRow));
        } catch (error) {
            notifyError(userMessage(error), "No se pudieron cargar los usuarios");
        }
    }

    document.getElementById("user-new").addEventListener("click", () => userModal.open(null, load));

    body.addEventListener("click", async event => {
        const button = event.target.closest("button[data-action]");
        if (!button) return;
        const user = users.find(item => item.id === Number(button.dataset.id));
        if (!user) return;
        if (button.dataset.action === "edit") userModal.open(user, load);
        if (button.dataset.action === "password") resetPassword(user);
        if (button.dataset.action === "sessions") endSessions(user);
    });

    // Loaded when the view is shown, so the list is never stale after changes elsewhere
    document.addEventListener(VIEW_SHOWN, event => {
        if (event.detail.view === "users") load();
    });
}

async function resetPassword(user) {
    const password = await promptNewPassword({
        title: `Nueva contraseña para ${user.full_name}`,
        text: "La cuenta se desbloquea y sale de todas sus sesiones abiertas.",
        minLength: MIN_PASSWORD_LENGTH,
    });
    if (!password) return;
    try {
        await usersApi.resetPassword(user.id, password);
        notifySuccess("Contraseña actualizada");
    } catch (error) {
        notifyError(userMessage(error));
    }
}

async function endSessions(user) {
    const confirmed = await confirmAction({
        title: "¿Cerrar todas sus sesiones?",
        text: `${user.full_name} tendrá que volver a iniciar sesión en todos sus navegadores.`,
        confirmText: "Sí, cerrar sesiones",
    });
    if (!confirmed) return;
    try {
        await usersApi.endSessions(user.id);
        notifySuccess("Sesiones cerradas");
    } catch (error) {
        notifyError(userMessage(error));
    }
}

function buildUserRow(user) {
    const row = document.createElement("tr");

    const who = document.createElement("td");
    who.className = "cell-client";
    who.dataset.label = "Usuario";
    const wrapper = document.createElement("span");
    wrapper.className = "client-link";
    const avatar = document.createElement("span");
    avatar.className = "avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = initials(user.full_name);
    const text = document.createElement("span");
    const name = document.createElement("span");
    name.className = "client-name d-block";
    name.textContent = user.full_name;
    const username = document.createElement("span");
    username.className = "small text-body-secondary";
    username.textContent = user.username;
    text.append(name, username);
    wrapper.append(avatar, text);
    who.appendChild(wrapper);

    const role = cell("Rol", user.role_label);

    const status = cell("Estado", "");
    const badge = document.createElement("span");
    const [label, className] = !user.is_active
        ? ["Desactivado", "status-archived"]
        : user.locked ? ["Bloqueado", "status-overdue"] : ["Activo", "status-completed"];
    badge.className = `badge rounded-pill status-badge ${className}`;
    badge.textContent = label;
    status.appendChild(badge);

    const lastLogin = cell("Último acceso", user.last_login_at ? formatDateTime(user.last_login_at) : "Nunca");
    lastLogin.classList.add("text-body-secondary");

    const actions = document.createElement("td");
    actions.className = "text-end cell-actions";
    const group = document.createElement("div");
    group.className = "row-actions";
    group.append(
        actionButton("edit", "btn-outline-primary", "bi-pencil", `Editar a ${user.full_name}`, user),
        actionButton("password", "btn-outline-secondary", "bi-key", `Nueva contraseña para ${user.full_name}`, user),
        actionButton("sessions", "btn-outline-secondary", "bi-box-arrow-right", `Cerrar las sesiones de ${user.full_name}`, user),
    );
    actions.appendChild(group);

    row.append(who, role, status, lastLogin, actions);
    return row;
}

function cell(label, text) {
    const td = document.createElement("td");
    td.dataset.label = label;
    td.textContent = text;
    return td;
}

function actionButton(action, variant, icon, label, user) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `btn btn-sm ${variant}`;
    button.dataset.action = action;
    button.dataset.id = user.id;
    button.title = label;
    button.setAttribute("aria-label", label);
    const iconElement = document.createElement("i");
    iconElement.className = `bi ${icon}`;
    iconElement.setAttribute("aria-hidden", "true");
    button.appendChild(iconElement);
    return button;
}
