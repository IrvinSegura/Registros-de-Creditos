// Entry point: wires the views and components together, leaving out what the role cannot use
import { initCreditDetail } from "./components/credit-detail.js";
import { initEditModal } from "./components/edit-modal.js";
import { initRouter } from "./lib/router.js";
import { can, PERMISSIONS } from "./lib/session.js";
import { initThemeToggle } from "./lib/theme.js";
import { initCredits } from "./views/credits.js";
import { initDashboard } from "./views/dashboard.js";
import { initRegisterForm } from "./views/register.js";

const editModal = can(PERMISSIONS.update) ? initEditModal() : null;
const creditDetail = initCreditDetail({ onEdit: editModal?.open });
if (can(PERMISSIONS.create)) initRegisterForm();
initCredits({ onView: creditDetail.open, onEdit: editModal?.open });
const dashboard = initDashboard({ onView: creditDetail.open });
initThemeToggle(() => dashboard.refreshTheme());
initRouter();
