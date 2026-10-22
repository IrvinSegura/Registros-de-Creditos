// Entry point: wires the page modules together
import { initCreditTable } from "./modules/credit-table.js";
import { initEditModal } from "./modules/edit-modal.js";
import { initRegisterForm } from "./modules/register-form.js";
import { initStats } from "./modules/stats.js";
import { initThemeToggle } from "./theme.js";

const editModal = initEditModal();
initRegisterForm();
initCreditTable({ onEdit: editModal.open });
const stats = initStats();
initThemeToggle(() => stats.refreshTheme());
