// SweetAlert2 is loaded globally from the CDN in base.html
const toast = Swal.mixin({
    toast: true,
    position: "top-end",
    showConfirmButton: false,
    timer: 2500,
    timerProgressBar: true,
});

const buttons = { buttonsStyling: false, reverseButtons: true };

export const notifySuccess = title => toast.fire({ icon: "success", title });

export function notifyError(text, title = "No se pudo completar la acción") {
    return Swal.fire({
        ...buttons,
        icon: "error",
        title,
        text,
        confirmButtonText: "Entendido",
        customClass: { confirmButton: "btn btn-primary" },
    });
}

async function confirm({ title, text, confirmText, icon, confirmClass }) {
    const result = await Swal.fire({
        ...buttons,
        icon,
        title,
        text,
        showCancelButton: true,
        focusCancel: true,
        confirmButtonText: confirmText,
        cancelButtonText: "Cancelar",
        customClass: { confirmButton: `btn ${confirmClass}`, cancelButton: "btn btn-outline-secondary" },
    });
    return result.isConfirmed;
}

export const confirmDanger = options => confirm({ ...options, icon: "warning", confirmClass: "btn-danger" });
export const confirmAction = options => confirm({ ...options, icon: "question", confirmClass: "btn-primary" });

// Asks for a new password twice; resolves to the password, or null when cancelled
export async function promptNewPassword({ title, text, minLength }) {
    const result = await Swal.fire({
        ...buttons,
        title,
        text,
        html: `
            <p class="small text-body-secondary mb-3"></p>
            <input type="password" id="swal-password" class="form-control mb-2" autocomplete="new-password"
                   placeholder="Nueva contraseña" aria-label="Nueva contraseña">
            <input type="password" id="swal-password-confirm" class="form-control" autocomplete="new-password"
                   placeholder="Repite la contraseña" aria-label="Repite la contraseña">`,
        didOpen: popup => {
            popup.querySelector("p").textContent = text;
            popup.querySelector("#swal-password").focus();
        },
        showCancelButton: true,
        confirmButtonText: "Guardar",
        cancelButtonText: "Cancelar",
        customClass: { confirmButton: "btn btn-primary", cancelButton: "btn btn-outline-secondary" },
        preConfirm: () => {
            const password = document.getElementById("swal-password").value;
            const confirmation = document.getElementById("swal-password-confirm").value;
            if (password.length < minLength) {
                Swal.showValidationMessage(`La contraseña debe tener al menos ${minLength} caracteres.`);
                return false;
            }
            if (password !== confirmation) {
                Swal.showValidationMessage("Las contraseñas no coinciden.");
                return false;
            }
            return password;
        },
    });
    return result.isConfirmed ? result.value : null;
}
