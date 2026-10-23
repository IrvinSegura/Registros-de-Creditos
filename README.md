# Sistema de Gestión de Créditos

## 📌 Descripción
Este proyecto es una aplicación web desarrollada en **Python (Flask) y SQLite** para la gestión de créditos otorgados a clientes. Permite registrar, listar, editar y eliminar créditos, además de visualizar los datos en gráficos interactivos utilizando **Chart.js**.<br>

## 🛠 Tecnologías Utilizadas
### Backend
- **Python** con **Flask** (Framework ligero para aplicaciones web).
- **SQLite** (Base de datos liviana y embebida).
- **SQLAlchemy** (ORM) y **Flask-Migrate / Alembic** (migraciones de base de datos).
- **marshmallow** y **flask-smorest** (validación, serialización y documentación OpenAPI).
### Frontend
- **HTML, CSS y JavaScript** (Interfaz de usuario).
- **Bootstrap** (Diseño responsivo y atractivo).
- **SweetAlert2** (Alertas interactivas y modernas).
- **Chart.js** (Generación de gráficos estadísticos).<br>
## 🚀 Funcionalidades
✅ Registro de créditos con **simulación en vivo de la cuota mensual** (sistema de cuota fija).<br>
✅ **Tabla de amortización** de cada crédito: fecha, cuota, interés, capital y saldo.<br>
✅ **Historial de cambios** de cada crédito: qué campo cambió, el valor anterior y el nuevo.<br>
✅ Listado con búsqueda, **orden por columna**, **filtros por fechas y montos**, paginación y **exportación a CSV**.<br>
✅ Panel con **filtro de periodo**, indicadores de cartera, monto por mes, créditos por plazo y **clientes con mayor monto**.<br>
✅ Validaciones en los formularios, alineadas con las de la API.<br>
✅ Menú lateral, tema claro y oscuro, y diseño adaptable a móvil.<br>
✅ **Inicio de sesión con roles** (Administrador, Analista y Consulta), bloqueo temporal tras intentos fallidos y protección CSRF.<br>
✅ Historial de cambios con **el usuario que hizo cada cambio**.<br>
✅ Cabeceras de seguridad (CSP con nonce, X-Frame-Options, nosniff) y librerías del CDN con **hashes de integridad (SRI)**.<br>
<br>
## 🔧 Instalación y Configuración
### 1️⃣ Requisitos Previos
- **Python 3.11** o superior.
- **Git** para clonar el repositorio.
### 2️⃣ Pasos de Instalación
```sh
# Clonar el repositorio
git clone https://github.com/IrvinSegura/Registros-de-Creditos
cd Registros-de-Creditos

# Crear y activar un entorno virtual
python -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate

# Instalar las dependencias (incluye las de desarrollo y pruebas)
pip install -r requirements-dev.txt

# Configurar variables de entorno
cp .env.example .env

# Crear la base de datos aplicando las migraciones
flask db upgrade

# Crear el primer usuario (pide el nombre y la contraseña)
flask users create admin --role admin

# Ejecutar la aplicación
flask run

# Acceder a la aplicación en el navegador
http://127.0.0.1:5000/
```

### 3️⃣ Variables de entorno
| Variable | Descripción | Valor por defecto |
|---|---|---|
| `APP_ENV` | `development`, `testing` o `production` | `development` |
| `SECRET_KEY` | Clave secreta de Flask (obligatoria en producción) | solo para desarrollo |
| `DATABASE_URL` | URL de la base de datos (las rutas SQLite relativas se crean en `instance/`) | `sqlite:///credits.db` |
| `CORS_ORIGINS` | Orígenes permitidos para llamar a `/api/*` desde otro dominio, separados por comas | vacío (ninguno) |

## 👥 Usuarios y roles
Toda la aplicación y la API requieren iniciar sesión. Las cuentas se administran desde la terminal:

```sh
flask users create <usuario> --role analyst   # admin | analyst | viewer
flask users list
flask users set-password <usuario>            # también desbloquea la cuenta
flask users deactivate <usuario>              # cierra sus sesiones abiertas
flask users activate <usuario>
```

| Rol | Consultar y exportar | Registrar y editar | Eliminar |
|---|:---:|:---:|:---:|
| `admin` (Administrador) | ✅ | ✅ | ✅ |
| `analyst` (Analista) | ✅ | ✅ | ❌ |
| `viewer` (Consulta) | ✅ | ❌ | ❌ |

- Las contraseñas se guardan con hash (scrypt) y deben tener al menos 10 caracteres.
- Tras 5 intentos fallidos la cuenta se bloquea 15 minutos.
- La sesión dura 8 horas; la cookie es `HttpOnly`, `SameSite=Lax` y, en producción, `Secure`.

## 🗂 Estructura del proyecto
```
app/
├── __init__.py        # Application factory (create_app)
├── config.py          # Configuración por entorno
├── extensions.py      # SQLAlchemy, Migrate, Api (OpenAPI), CORS
├── errors.py          # Errores de dominio y su respuesta JSON
├── security.py        # Cabeceras de seguridad, Content Security Policy y tokens CSRF
├── auth/              # Inicio de sesión, protección de rutas y permisos por rol
├── cli.py             # Comandos `flask users ...`
├── models/            # Modelos SQLAlchemy: crédito e historial de cambios
├── schemas/           # Validación y serialización (marshmallow)
├── services/          # Lógica de negocio y cálculo de amortización, sin dependencias de HTTP
├── api/v1/            # Endpoints REST versionados
├── web/               # Páginas renderizadas en el servidor
├── templates/
│   ├── base.html      # Esqueleto HTML: tema y librerías
│   ├── app.html       # Layout de la aplicación: menú lateral, barra superior y usuario
│   ├── index.html     # Vistas de la aplicación
│   ├── auth/          # Página de inicio de sesión
│   ├── macros/        # Campos de formulario compartidos
│   ├── views/         # Una plantilla por vista: dashboard, credits, register
│   └── components/    # Paneles compartidos: credit-detail, edit-modal
└── static/            # css/ y js/ siguen la misma organización que templates/
    ├── img/           # Favicon
    ├── css/
    │   ├── base.css   # Variables de diseño (tema claro y oscuro), menú, tarjetas, formularios y botones
    │   ├── views/     # Estilos de cada vista
    │   └── components/
    └── js/
        ├── main.js    # Punto de entrada que conecta las vistas y los componentes
        ├── lib/       # API, enrutador, formularios, formato (es-MX), avisos, tema y acciones de crédito
        ├── views/     # dashboard, credits, register
        └── components/ # credit-detail, edit-modal, credit-rows, quote-panel, portfolio-charts
migrations/            # Migraciones de base de datos (Alembic)
tests/                 # Pruebas con pytest
wsgi.py                # Punto de entrada
```

## 📡 API REST
La documentación interactiva (Swagger UI) está en **`/api/docs`** y la especificación OpenAPI en `/api/openapi.json`.

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/credits` | Lista paginada. Filtros: `client_name`, `issue_date_from`, `issue_date_to`, `amount_min`, `amount_max`. Orden: `sort` y `order` (`asc`/`desc`) |
| `POST` | `/api/v1/credits` | Registra un crédito |
| `GET` | `/api/v1/credits/export` | Descarga en CSV los créditos con los mismos filtros y orden |
| `GET` | `/api/v1/credits/quote?amount=10000&interest_rate=12&term_months=12` | Simula la cuota mensual, los intereses y el total a pagar |
| `GET` | `/api/v1/credits/summary` | Totales, promedios, monto por mes, créditos por plazo y clientes con mayor monto; acepta `issue_date_from` e `issue_date_to` |
| `GET` | `/api/v1/credits/{id}` | Obtiene un crédito |
| `PUT` | `/api/v1/credits/{id}` | Actualiza un crédito |
| `DELETE` | `/api/v1/credits/{id}` | Elimina un crédito y su historial |
| `GET` | `/api/v1/credits/{id}/amortization` | Tabla de amortización del crédito |
| `GET` | `/api/v1/credits/{id}/history` | Historial de cambios, del más reciente al más antiguo |

Todas las rutas requieren una sesión iniciada (sin ella responden `401`). Las peticiones que modifican datos (`POST`, `PUT`, `DELETE`) deben enviar además la cabecera `X-CSRF-Token` con el token de la página, y el rol del usuario debe permitir la acción (si no, `403`).

La tasa de interés es **anual** y se paga mensualmente. La cuota se calcula con el sistema de cuota fija (francés) y la última cuota absorbe el redondeo para que el saldo termine exactamente en cero.

Los montos y tasas se manejan como decimales exactos y se devuelven como texto (`"15000.50"`). Los errores siguen siempre el mismo formato:
```json
{"code": 422, "status": "Unprocessable Entity", "errors": {"json": {"term_months": ["El plazo debe estar entre 1 y 360 meses."]}}}
```

## 🧪 Pruebas
```sh
pytest
```

## 🗃 Migraciones
```sh
# Después de modificar un modelo
flask db migrate -m "descripción del cambio"
flask db upgrade
```
<br>

![image](https://github.com/user-attachments/assets/05947930-722f-47b2-b8eb-c0b8cbf3e715)
![image](https://github.com/user-attachments/assets/4fd6cb11-8429-4b87-8fd8-71d61e265eb7)
![image](https://github.com/user-attachments/assets/cecda054-9030-4c62-a22f-89b6118b8e1e)
![image](https://github.com/user-attachments/assets/88c6c9e8-1352-47c5-8ce4-39318e0f3fca)



