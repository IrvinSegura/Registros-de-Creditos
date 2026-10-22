// Entry point: wires the page modules together
import { initCreditDetail } from "./modules/credit-detail.js";
import { initCredits } from "./modules/credits.js";
import { initDashboard } from "./modules/dashboard.js";
import { initEditModal } from "./modules/edit-modal.js";
import { initRegisterForm } from "./modules/register.js";
import { initRouter } from "./router.js";
import { initThemeToggle } from "./theme.js";

const editModal = initEditModal();
const creditDetail = initCreditDetail({ onEdit: editModal.open });
initRegisterForm();
initCredits({ onView: creditDetail.open, onEdit: editModal.open });
const dashboard = initDashboard();
initThemeToggle(() => dashboard.refreshTheme());
initRouter();
