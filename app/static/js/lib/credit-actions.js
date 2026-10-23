// Credit actions shared by the table and the detail panel
import { creditsApi, userMessage } from "./api.js";
import { notifyCreditsChanged } from "./events.js";
import { confirmDanger, notifyError, notifySuccess } from "./notify.js";

// Asks for confirmation first; resolves to true only when the credit was deleted
export async function deleteCredit(id, clientName) {
    const confirmed = await confirmDanger({
        title: "¿Eliminar este crédito?",
        text: `Se eliminará el crédito de ${clientName} junto con su historial. Esta acción no se puede deshacer.`,
        confirmText: "Sí, eliminar",
    });
    if (!confirmed) return false;

    try {
        await creditsApi.remove(id);
        notifySuccess("Crédito eliminado");
        notifyCreditsChanged();
        return true;
    } catch (error) {
        notifyError(userMessage(error));
        return false;
    }
}
