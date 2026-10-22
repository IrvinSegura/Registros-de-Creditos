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
✅ Registro de nuevos créditos mediante un formulario.<br>
✅ Listado de créditos en una tabla con paginación.<br>
✅ Edición y eliminación de créditos existentes.<br>
✅ Validaciones en los formularios para evitar datos incorrectos.<br>
✅ Visualización gráfica de los créditos otorgados.<br>
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

## 🗂 Estructura del proyecto
```
app/
├── __init__.py        # Application factory (create_app)
├── config.py          # Configuración por entorno
├── extensions.py      # SQLAlchemy, Migrate, Api (OpenAPI), CORS
├── errors.py          # Errores de dominio y su respuesta JSON
├── models/            # Modelos SQLAlchemy
├── schemas/           # Validación y serialización (marshmallow)
├── services/          # Lógica de negocio, sin dependencias de HTTP
├── api/v1/            # Endpoints REST versionados
├── web/               # Páginas renderizadas en el servidor
├── templates/
└── static/
migrations/            # Migraciones de base de datos (Alembic)
tests/                 # Pruebas con pytest
wsgi.py                # Punto de entrada
```

## 📡 API REST
La documentación interactiva (Swagger UI) está en **`/api/docs`** y la especificación OpenAPI en `/api/openapi.json`.

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/v1/credits?page=1&per_page=10&client_name=ana` | Lista paginada con filtro opcional por cliente |
| `POST` | `/api/v1/credits` | Registra un crédito |
| `GET` | `/api/v1/credits/{id}` | Obtiene un crédito |
| `PUT` | `/api/v1/credits/{id}` | Actualiza un crédito |
| `DELETE` | `/api/v1/credits/{id}` | Elimina un crédito |

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



