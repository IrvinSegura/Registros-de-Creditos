[33m197b009[m[33m ([m[1;36mHEAD[m[33m -> [m[1;32mfeat/period-picker[m[33m)[m feat(ui): use the period picker in the dashboard
 app/static/css/views/dashboard.css | 141 [32m+++++++++++++++++++++++++++++++[m[31m------[m
 app/static/js/views/dashboard.js   |  51 [32m+[m[31m-------------[m
 app/templates/views/dashboard.html |  55 [32m+++++++++++[m[31m----[m
 3 files changed, 163 insertions(+), 84 deletions(-)
[33m6f5f4e6[m feat(ui): add a period picker with presets and a custom range dropdown
 app/static/js/components/period-picker.js | 106 [32m++++++++++++++++++++++++++++++[m
 1 file changed, 106 insertions(+)
[33m5423c6a[m[33m ([m[1;31morigin/feat/portfolio-status[m[33m, [m[1;32mfeat/portfolio-status[m[33m)[m docs: describe credit standing and the new dashboard figures
 README.md | 9 [32m++++++[m[31m---[m
 1 file changed, 6 insertions(+), 3 deletions(-)
[33m0b84063[m style(tests): add the blank line flake8 expects in the app fixture
 tests/conftest.py | 1 [32m+[m
 1 file changed, 1 insertion(+)
[33m0b67e2e[m feat(ui): add status, progress and the next installment to the credit detail
 app/static/css/components/credit-detail.css | 85 [32m+++++++++++++++++++++++++++++[m
 app/static/js/components/credit-detail.js   | 36 [32m+++++++++++[m[31m-[m
 app/static/js/main.js                       |  2 [32m+[m[31m-[m
 app/templates/components/credit-detail.html | 21 [32m++++++[m[31m-[m
 4 files changed, 140 insertions(+), 4 deletions(-)
[33mb9f22e5[m feat(ui): show installment progress and outstanding balance in the credits table
 app/static/css/base.css                 | 21 [32m+++++++++++++++[m
 app/static/css/views/credits.css        | 47 [32m++++++++++++++++++++++++++[m[31m-------[m
 app/static/js/components/credit-rows.js | 45 [32m++++++++++++++++++++++++++[m[31m-----[m
 app/templates/views/credits.html        |  3 [32m++[m[31m-[m
 4 files changed, 99 insertions(+), 17 deletions(-)
[33m42ef51a[m feat(ui): add outstanding balance, weighted rate and upcoming payments to the dashboard
 app/static/css/views/dashboard.css | 120 [32m+++++++++++++++++++[m[31m-[m
 app/static/js/lib/format.js        |   7 [32m++[m
 app/static/js/views/dashboard.js   | 217 [32m+++++++++++++++++++++++++++++++++++++[m
 app/templates/views/dashboard.html |  56 [32m+++++++[m[31m---[m
 4 files changed, 383 insertions(+), 17 deletions(-)
[33m06fb90b[m feat(api): report credit standing, portfolio balance and upcoming payments
 app/schemas/credit.py          | 31 [32m+++++++++++++++++++[m
 app/services/credit_service.py | 67 [32m+++++++++++++++++++++++++++++++++++[m[31m-------[m
 tests/test_credit_insights.py  | 47 [32m++++++++++++++++++++++++++++[m[31m-[m
 3 files changed, 134 insertions(+), 11 deletions(-)
[33m2dee6cd[m feat(api): compute where each credit stands from its payment schedule
 app/models/credit.py         |  6 [32m++++++[m
 app/services/amortization.py | 31 [32m+++++++++++++++++++++++++++++++[m
 tests/test_amortization.py   | 30 [32m++++++++++++++++++++++++++++++[m
 3 files changed, 67 insertions(+)
[33m7301986[m[33m ([m[1;31morigin/feat/auth[m[33m, [m[1;32mfeat/auth[m[33m)[m docs: explain accounts, roles and the session requirements of the API
 README.md | 36 [32m++++++++++++++++++++++++++++++++++[m[31m--[m
 1 file changed, 34 insertions(+), 2 deletions(-)
[33m9ef41a7[m test(auth): cover sign-in, roles, CSRF and the users commands
 tests/conftest.py  |  59 [32m+++++++++++[m[31m-[m
 tests/test_auth.py | 266 [32m+++++++++++++++++++++++++++++++++++++++++++++++++++++[m
 2 files changed, 324 insertions(+), 1 deletion(-)
[33m720b061[m feat(ui): hide the register shortcuts from read-only roles
 app/templates/views/credits.html   | 2 [32m++[m
 app/templates/views/dashboard.html | 4 [32m++++[m
 2 files changed, 6 insertions(+)
[33ma2b3f66[m feat(ui): show only the credit actions the role allows
 app/static/js/components/credit-detail.js   |  10 [32m+[m[31m-[m
 app/static/js/components/credit-rows.js     |  13 [32m++[m[31m-[m
 app/static/js/views/credits.js              | 160 [32m++++++++++++++++++++++++++++[m
 app/templates/components/credit-detail.html |   8 [32m+[m[31m-[m
 4 files changed, 185 insertions(+), 6 deletions(-)
[33mce705d2[m feat(ui): send the CSRF token and sign in again when the session expires
 app/static/js/lib/api.js     | 14 [32m+++++++++++++[m[31m-[m
 app/static/js/lib/router.js  | 10 [32m++++++++[m[31m--[m
 app/static/js/lib/session.js | 17 [32m+++++++++++++++++[m
 app/static/js/main.js        | 25 [32m+++++++++++++[m[31m------------[m
 4 files changed, 51 insertions(+), 15 deletions(-)
[33m6888f81[m feat(ui): add the app layout with the signed-in user and sign-out
 app/static/css/base.css  |  58 [32m+++++++++++++++++++++++++[m
 app/templates/app.html   | 111 [32m+++++++++++++++++++++++++++++++++++++++++++++++[m
 app/templates/index.html |   6 [32m++[m[31m-[m
 3 files changed, 174 insertions(+), 1 deletion(-)
[33mec4aa13[m feat(ui): add the sign-in page
 app/static/css/views/login.css | 133 [32m+++++++++++++++++++++++++++++++++++++++++[m
 app/static/js/login.js         |  28 [32m+++++++++[m
 app/templates/auth/login.html  |  90 [32m++++++++++++++++++++++++++++[m
 app/templates/base.html        |  85 [32m++[m[31m------------------------[m
 4 files changed, 257 insertions(+), 79 deletions(-)
[33m37e8bff[m feat(api): check roles on write endpoints and record who changes a credit
 app/api/v1/credits.py          | 29 [32m+++++++++++++++++++++++[m[31m------[m
 app/schemas/credit.py          |  4 [32m++++[m
 app/services/credit_service.py | 10 [32m++++++[m[31m----[m
 3 files changed, 33 insertions(+), 10 deletions(-)
[33mf74c662[m feat(auth): require sign-in on every route and add the users commands
 app/__init__.py      |  8 [32m++++++[m[31m-[m
 app/auth/__init__.py | 39 [32m++++++++++++++++++++++++++++++[m
 app/auth/views.py    | 48 [32m+++++++++++++++++++++++++++++++++++++[m
 app/cli.py           | 68 [32m++++++++++++++++++++++++++++++++++++++++++++++++++++[m
 4 files changed, 162 insertions(+), 1 deletion(-)
[33m06fd1cb[m feat(auth): add CSRF tokens and harden the session cookie
 app/config.py   |  9 [32m+++++++++[m
 app/security.py | 53 [32m+++++++++++++++++++++++++++++++++++++++++++++++++++[m[31m--[m
 2 files changed, 60 insertions(+), 2 deletions(-)
[33me30a395[m feat(auth): add roles, sign-in checks with lockout and change authors
 app/auth/permissions.py                            |  66 [32m+++++++++[m
 app/models/credit_change.py                        |   4 [32m+[m
 app/services/user_service.py                       | 149 [32m+++++++++++++++++++++[m
 .../a0466543d65d_add_users_and_change_authors.py   |  49 [32m+++++++[m
 4 files changed, 268 insertions(+)
[33mf42dbfe[m feat(auth): add Flask-Login and the user model
 app/extensions.py      |  2 [32m++[m
 app/models/__init__.py |  3 [32m++[m[31m-[m
 app/models/user.py     | 28 [32m++++++++++++++++++++++++++++[m
 requirements.txt       |  1 [32m+[m
 4 files changed, 33 insertions(+), 1 deletion(-)
[33ma3ebabe[m[33m ([m[1;31morigin/feat/ui-polish[m[33m, [m[1;32mfeat/ui-polish[m[33m)[m docs: describe the new frontend layout
 README.md | 20 [32m+++++++++++[m[31m---------[m
 1 file changed, 11 insertions(+), 9 deletions(-)
[33me666e1e[m feat(ui): fit the credits table to its card and load the split stylesheets
 app/static/css/components/credit-detail.css | 182 [32m++++++++++++++++++[m
 app/static/css/views/credits.css            | 275 [32m++++++++++++++++++++++++++++[m
 app/templates/base.html                     |   5 [32m+[m[31m-[m
 3 files changed, 461 insertions(+), 1 deletion(-)
[33ma169cb4[m refactor(ui): split the stylesheet into base and per-view files
 app/static/css/app.css             | 1132 [31m------------------------------------[m
 app/static/css/base.css            |  474 [32m+++++++++++++++[m
 app/static/css/views/dashboard.css |  194 [32m++++++[m
 app/static/css/views/register.css  |  110 [32m++++[m
 4 files changed, 778 insertions(+), 1132 deletions(-)
[33m67e0035[m refactor(ui): move the panel templates into components/
 app/templates/{partials => components}/credit-detail.html |  0
 app/templates/{partials => components}/edit-modal.html    |  0
 app/templates/index.html                                  | 12 [32m++++++[m[31m------[m
 3 files changed, 6 insertions(+), 6 deletions(-)
[33m52dde19[m refactor(ui): move the view templates into views/
 app/templates/{partials => views}/credits.html   | 4 [32m++[m[31m--[m
 app/templates/{partials => views}/dashboard.html | 0
 app/templates/{partials => views}/register.html  | 0
 3 files changed, 2 insertions(+), 2 deletions(-)
[33mcc354df[m refactor(ui): move the credits and dashboard views into views/
 .../register.js => components/quote-panel.js}      | 53 [32m+++[m[31m-------------------[m
 app/static/js/views/register.js                    | 46 [32m+++++++++++++++++++[m
 2 files changed, 52 insertions(+), 47 deletions(-)
[33m58bb4b9[m refactor(ui): move the panels into components/ and extract table rows and charts
 .../js/{modules => components}/credit-detail.js    | 10 [32m+[m[31m--[m
 app/static/js/components/credit-rows.js            | 97 [32m++++++++++++++++++++++[m
 .../js/{modules => components}/edit-modal.js       | 10 [32m+[m[31m--[m
 app/static/js/components/portfolio-charts.js       | 89 [32m++++++++++++++++++++[m
 4 files changed, 196 insertions(+), 10 deletions(-)
[33m39dfb60[m refactor(ui): move the remaining helpers into lib/ and share the delete action
 app/static/js/lib/credit-actions.js | 24 [32m++++++++++++++++++++++++[m
 app/static/js/{ => lib}/notify.js   |  0
 app/static/js/{ => lib}/router.js   |  0
 app/static/js/{ => lib}/theme.js    |  0
 4 files changed, 24 insertions(+)
[33m5611be4[m refactor(ui): move the API client and form helpers into lib/
 app/static/js/{ => lib}/api.js    | 0
 app/static/js/{ => lib}/events.js | 0
 app/static/js/{ => lib}/format.js | 0
 app/static/js/{ => lib}/forms.js  | 0
 4 files changed, 0 insertions(+), 0 deletions(-)
[33ma8041cc[m[33m ([m[1;31morigin/fix/validation[m[33m, [m[1;32mfix/validation[m[33m)[m ci: install the pinned dev requirements and drop the PyPI publish template
 .github/workflows/python-app.yml     |  5 [32m+[m[31m--[m
 .github/workflows/python-publish.yml | 70 [31m------------------------------------[m
 2 files changed, 3 insertions(+), 72 deletions(-)
[33m7257e05[m chore(ui): remove an unused hidden field from the edit modal
 app/templates/partials/edit-modal.html | 1 [31m-[m
 1 file changed, 1 deletion(-)
[33mec086aa[m fix(ui): apply the same amount, decimal and date rules in the credit forms
 app/static/js/forms.js            | 32 [32m++++++++++++++++++++++++++[m[31m------[m
 app/static/js/modules/register.js |  7 [32m+++++[m[31m--[m
 2 files changed, 31 insertions(+), 8 deletions(-)
[33m607369b[m fix(api): explain the amount limit, reject extra decimals and future issue dates
 app/schemas/credit.py     | 45 [32m+++++++++++++++++++++++++++++++++++[m[31m----------[m
 tests/test_credits_api.py | 22 [32m++++++++++++++++++++++[m
 2 files changed, 57 insertions(+), 10 deletions(-)
