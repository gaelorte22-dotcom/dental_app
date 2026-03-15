# 🦷 DentalApp — Sistema de Gestión Odontológica

Aplicación de escritorio para consultorio dental, desarrollada con **Python + PyQt6 + SQLite**.

---

## 📁 Estructura del proyecto

```
dental_app/
├── main.py                  # Punto de entrada — ventana principal
├── requirements.txt         # Dependencias
├── database/
│   ├── __init__.py
│   └── db_manager.py        # SQLite CRUD (pacientes, citas, historial, pagos)
└── modules/
    ├── __init__.py
    └── pacientes.py         # Módulo de gestión de pacientes (✅ listo)
```

---

## 🚀 Instalación y ejecución

### 1. Crear entorno virtual (recomendado)
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Ejecutar la app
```bash
python main.py
```

---

## ✅ Módulos incluidos

| Módulo         | Estado         | Descripción                              |
|----------------|----------------|------------------------------------------|
| Pacientes      | ✅ Completo     | Registro, búsqueda, edición, eliminación |
| Citas          | 🔜 Próximamente | Agenda por día/semana                    |
| Expedientes    | 🔜 Próximamente | Historial clínico y odontograma          |
| Facturación    | 🔜 Próximamente | Cobros y pagos                           |

---

## 🗄️ Base de datos

Se usa **SQLite** — no requiere servidor. El archivo `dental_clinic.db` se crea
automáticamente en la carpeta `database/` al ejecutar la app por primera vez.

---

## 🛠 Tecnologías

- **Python 3.10+**
- **PyQt6** — interfaz de usuario
- **SQLite** — base de datos local
