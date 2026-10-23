// Credit actions shared by the table and the detail panel; each resolves to true when it went through
import { creditsApi, userMessage } from "./api.js";
import { notifyCreditsChanged } from "./events.js";
import { confirmAction, confirmDanger, notifyError, notifySuccess } from "./notify.js";

async function run(action, successMessage) {
    try {
        await action();
        notifySuccess(successMessage);
        notifyCreditsChanged();
        return true;
    } catch (error) {
        notifyError(userMessage(error));
        return false;
    }
}

export async function archiveCredit(id, clientName) {
    const confirmed = await confirmAction({
        title: "¿Archivar este crédito?",
        text: `El crédito de ${clientName} saldrá de la cartera y del panel, y ya no se podrá editar ni registrarle pagos. `
            + "Conserva sus datos, pagos e historial, y puedes restaurarlo cuando quieras.",
        confirmText: "Sí, archivar",
    });
    return confirmed && run(() => creditsApi.archive(id), "Crédito archivado");
}

export const restoreCredit = id => run(() => creditsApi.restore(id), "Crédito restaurado");

// Only for archived credits
export async function deleteCreditForGood(id, clientName) {
    const confirmed = await confirmDanger({
        title: "¿Eliminar definitivamente?",
        text: `Se borrará el crédito de ${clientName} con sus pagos e historial. Esta acción no se puede deshacer.`,
        confirmText: "Sí, eliminar",
    });
    return confirmed && run(() => creditsApi.remove(id), "Crédito eliminado");
}
