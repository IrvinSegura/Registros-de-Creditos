// A credit's status as the user reads it: archived first, otherwise its standing
const LABELS = { active: "Vigente", overdue: "Atrasado", completed: "Concluido", archived: "Archivado" };

export const creditStatus = credit => (credit.archived_at ? "archived" : credit.standing.status);

export function buildStatusBadge(status) {
    const badge = document.createElement("span");
    badge.className = `badge rounded-pill status-badge status-${status}`;
    badge.textContent = LABELS[status];
    return badge;
}

export const statusLabel = status => LABELS[status];
