// What the signed-in user may do, rendered by the server on <body data-permissions>.
// Only used to hide controls: the API checks every permission again.
export const PERMISSIONS = {
    create: "credits:create",
    update: "credits:update",
    delete: "credits:delete",
};

const granted = new Set((document.body.dataset.permissions ?? "").split(" ").filter(Boolean));

export const can = permission => granted.has(permission);

// Sends the user to the sign-in page and brings them back to the current view afterwards
export function redirectToLogin() {
    const next = `${window.location.pathname}${window.location.hash}`;
    window.location.assign(`/login?next=${encodeURIComponent(next)}`);
}
