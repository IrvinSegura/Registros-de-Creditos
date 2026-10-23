from decimal import Decimal

from playwright.sync_api import expect

from app.extensions import db
from app.models import Credit
from app.services import user_service
from tests.e2e.conftest import PASSWORD, sign_in

NEW_PASSWORD = "e2e-new-password-456"


def toast(page):
    # The confirmation toast; the same words may also appear in the credit's history
    return page.locator(".swal2-toast .swal2-title")


def open_credits(page):
    page.get_by_role("link", name="Créditos", exact=True).click()
    page.wait_for_url("**/#/creditos")


def test_admin_registers_a_credit_and_records_a_payment(page):
    sign_in(page, "admin")
    page.get_by_role("link", name="Nuevo crédito", exact=True).first.click()

    page.locator("#client_name").fill("Lucía Prueba")
    page.locator("#amount").fill("12000")
    page.locator("#interest_rate").fill("12")
    page.locator("#term_months").fill("12")
    expect(page.locator("#quote-payment")).to_have_text("$1,066.19")
    page.locator("#credit-form button[type='submit']").click()
    expect(toast(page)).to_have_text("Crédito registrado")

    open_credits(page)
    page.locator("#credits-body").get_by_text("Lucía Prueba").click()
    page.locator("#detail-payments-tab").click()
    expect(page.locator("#payment-amount")).to_have_value("1066.19")
    page.locator("#payment-note").fill("Recibo 1")
    page.locator("#payment-form button[type='submit']").click()

    expect(toast(page)).to_have_text("Pago registrado")
    expect(page.locator("#detail-payments-count")).to_have_text("1")
    expect(page.locator("#detail-payments-list")).to_contain_text("Recibo 1")
    expect(page.locator("#detail-progress-label")).to_have_text("1 de 12 cuotas pagadas")


def test_overdue_credits_show_on_the_dashboard_and_in_the_filter(page, seed_credit):
    seed_credit(client_name="Rosa Atrasada", months_ago=3)
    seed_credit(client_name="Pedro Puntual")
    sign_in(page, "admin")

    expect(page.locator("#kpi-credit-status")).to_have_text("1 vigente · 1 atrasado · 0 concluidos")
    expect(page.locator("#kpi-overdue")).to_contain_text("vencido sin pagar")
    expect(page.locator("#upcoming-payments")).to_contain_text("Vencido hace")

    open_credits(page)
    page.locator("#status-filter").select_option("overdue")
    rows = page.locator("#credits-body tr")
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("Rosa Atrasada")
    expect(rows.first).to_contain_text("Vencido")

    xlsx = page.locator("[data-export='xlsx']")
    expect(xlsx).to_have_attribute("href", "/api/v1/credits/export?status=overdue&sort=id&order=asc&format=xlsx")
    response = page.request.get(xlsx.get_attribute("href"))
    assert response.ok
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")


def test_admin_archives_and_restores_a_credit(page, seed_credit):
    seed_credit(client_name="Marta Archivo")
    sign_in(page, "admin")
    open_credits(page)

    page.get_by_role("button", name="Archivar crédito de Marta Archivo").click()
    page.get_by_role("button", name="Sí, archivar").click()
    expect(toast(page)).to_have_text("Crédito archivado")
    expect(page.locator("#credits-empty")).to_be_visible()

    page.locator("#status-filter").select_option("archived")
    page.get_by_role("button", name="Restaurar crédito de Marta Archivo").click()
    expect(toast(page)).to_have_text("Crédito restaurado")
    page.locator("#status-filter").select_option("")
    expect(page.locator("#credits-body")).to_contain_text("Marta Archivo")


def test_detail_panel_closes_when_changing_views(page, seed_credit):
    seed_credit(client_name="Rosa Prueba")
    sign_in(page, "admin")
    open_credits(page)
    page.locator("#credits-body").get_by_text("Rosa Prueba").click()
    expect(page.locator("#credit-detail")).to_be_visible()

    # The sidebar sits under the panel's backdrop, so change the view through the address
    page.evaluate("window.location.hash = '#/panel'")

    expect(page.locator("#credit-detail")).to_be_hidden()


def test_toasts_are_readable_in_dark_mode(page):
    page.add_init_script("localStorage.setItem('theme', 'dark')")
    sign_in(page, "admin")
    # void: Swal.fire returns a promise that only settles when the toast closes
    page.evaluate("void Swal.fire({ toast: true, timer: 5000, icon: 'success', title: 'Prueba' })")

    colors = toast(page).evaluate(
        "title => [getComputedStyle(title.closest('.swal2-popup')).backgroundColor, getComputedStyle(title).color]"
    )
    assert colors[0] != "rgb(255, 255, 255)"
    assert colors[0] != colors[1]


def test_viewer_gets_a_read_only_interface(page, seed_credit):
    seed_credit(client_name="Rosa Prueba", months_ago=2)
    sign_in(page, "viewer")

    expect(page.locator("#topbar-new")).to_have_count(0)
    expect(page.get_by_role("link", name="Usuarios")).to_have_count(0)
    open_credits(page)
    expect(page.locator("#credits-body button[data-action='edit']")).to_have_count(0)
    expect(page.locator("#credits-body button[data-action='archive']")).to_have_count(0)

    page.locator("#credits-body").get_by_text("Rosa Prueba").click()
    expect(page.locator("#detail-statement-toggle")).to_be_visible()
    expect(page.locator("#payment-form")).to_have_count(0)
    expect(page.locator("#detail-edit")).to_have_count(0)


def test_saving_over_someone_elses_changes_is_refused(page, seed_credit, live_app):
    credit_id = seed_credit(client_name="Rosa Prueba")
    sign_in(page, "admin")
    open_credits(page)
    page.get_by_role("button", name="Editar crédito de Rosa Prueba").click()
    expect(page.locator("#edit-credit-modal")).to_be_visible()

    # Someone else saves the credit while the modal is open
    with live_app.app_context():
        credit = db.session.get(Credit, credit_id)
        credit.amount = Decimal("15000")
        db.session.commit()

    page.locator("#edit-term_months").fill("24")
    page.locator("#edit-credit-form button[type='submit']").click()

    expect(page.get_by_text("El crédito cambió")).to_be_visible()
    expect(page.get_by_text("Otra persona modificó este crédito")).to_be_visible()


def test_admin_creates_a_user(page):
    sign_in(page, "admin")
    page.get_by_role("link", name="Usuarios").click()
    page.get_by_role("button", name="Nuevo usuario").click()

    page.locator("#user-username").fill("marco")
    page.locator("#user-full_name").fill("Marco Ruiz")
    page.locator("#user-role").select_option("analyst")
    page.locator("#user-password").fill("short")
    page.locator("#user-form button[type='submit']").click()
    expect(page.locator("#user-password-error")).to_contain_text("al menos 10 caracteres")

    page.locator("#user-password").fill(NEW_PASSWORD)
    page.locator("#user-form button[type='submit']").click()
    expect(toast(page)).to_have_text("Usuario creado")
    expect(page.locator("#users-body")).to_contain_text("Marco Ruiz")


def test_users_change_their_own_password(page, live_app):
    with live_app.app_context():
        user_service.create_user("pablo", "Pablo Paz", PASSWORD, "analyst")
    sign_in(page, "pablo")

    page.locator("#account-password").click()
    page.locator("#password-current_password").fill(PASSWORD)
    page.locator("#password-new_password").fill(NEW_PASSWORD)
    page.locator("#password-confirm").fill("something-else-1")
    page.locator("#password-form button[type='submit']").click()
    expect(page.locator("#password-confirm-error")).to_have_text("Las contraseñas no coinciden.")

    page.locator("#password-confirm").fill(NEW_PASSWORD)
    page.locator("#password-form button[type='submit']").click()
    expect(toast(page)).to_have_text("Contraseña actualizada")

    # This session stays open; the new password works from now on
    open_credits(page)
    page.get_by_role("button", name="Cerrar sesión").click()
    sign_in(page, "pablo", NEW_PASSWORD)
