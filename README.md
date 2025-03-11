# Sistema de Gestión de Créditos

## 📌 Descripción
Este proyecto es una aplicación web desarrollada en **Python (Flask) y SQLite** para la gestión de créditos otorgados a clientes. Permite registrar, listar, editar y eliminar créditos, además de visualizar los datos en gráficos interactivos utilizando **Chart.js**.<br>

## 🛠 Tecnologías Utilizadas
### Backend
- **Python** con **Flask** (Framework ligero para aplicaciones web).
- **SQLite** (Base de datos liviana y embebida).
- **SQLAlchemy** (ORM para manejar la base de datos con facilidad).
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
- Tener instalado **Python 3.x**.
- Disponer de **Git** para clonar el repositorio.
- Instalar **un entorno virtual (opcional pero recomendado)**.<br>
### 2️⃣ Pasos de Instalación
```sh
# Clonar el repositorio
git clone https://github.com/IrvinSegura/Registros-de-Creditos
cd Registros-de-Creditos

# Crear y activar un entorno virtual (Opcional pero recomendado)
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar las dependencias
pip install flask flask_sqlalchemy flask_cors

# Ejecutar la aplicación
python app.py

# Acceder a la aplicación en el navegador
http://127.0.0.1:5000/
```
<br>
