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

export async function confirmDanger({ title, text, confirmText }) {
    const result = await Swal.fire({
        ...buttons,
        icon: "warning",
        title,
        text,
        showCancelButton: true,
        focusCancel: true,
        confirmButtonText: confirmText,
        cancelButtonText: "Cancelar",
        customClass: { confirmButton: "btn btn-danger", cancelButton: "btn btn-outline-secondary" },
    });
    return result.isConfirmed;
}
