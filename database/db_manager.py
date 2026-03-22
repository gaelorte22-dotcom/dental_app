import sqlite3
import os
import sys
from datetime import datetime

# Carpeta persistente cross-platform
def _get_app_data_dir():
    if sys.platform == "win32" or os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.path.expanduser("~")
    app_dir = os.path.join(base, "DentalApp")
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

APP_DATA_DIR = _get_app_data_dir()
DB_PATH = os.path.join(APP_DATA_DIR, "dental_clinic.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            fecha_nacimiento TEXT,
            genero TEXT,
            telefono TEXT,
            email TEXT,
            direccion TEXT,
            numero_seguro TEXT,
            alergias TEXT,
            notas TEXT,
            fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
            activo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS citas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            duracion INTEGER DEFAULT 30,
            motivo TEXT,
            estado TEXT DEFAULT 'pendiente',
            notas TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
        );

        CREATE TABLE IF NOT EXISTS historial_clinico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            tratamiento TEXT,
            diente TEXT,
            descripcion TEXT,
            costo REAL DEFAULT 0,
            dentista TEXT,
            estado TEXT DEFAULT 'realizado',
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
        );

        CREATE TABLE IF NOT EXISTS odontograma (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            diente_num INTEGER NOT NULL,
            estado TEXT DEFAULT 'sano',
            color TEXT DEFAULT '#27AE60',
            notas TEXT,
            fecha_actualizacion TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(paciente_id, diente_num),
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
        );

        CREATE TABLE IF NOT EXISTS recetas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            medicamentos TEXT,
            indicaciones TEXT,
            dentista TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
        );

        CREATE TABLE IF NOT EXISTS archivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            nombre TEXT,
            ruta TEXT,
            tipo TEXT,
            descripcion TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
        );

        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            concepto TEXT,
            monto_total REAL DEFAULT 0,
            monto_pagado REAL DEFAULT 0,
            metodo_pago TEXT,
            estado TEXT DEFAULT 'pagado',
            notas TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
        );

        CREATE TABLE IF NOT EXISTS abonos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pago_id INTEGER NOT NULL,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            monto REAL NOT NULL,
            metodo_pago TEXT,
            notas TEXT,
            FOREIGN KEY (pago_id) REFERENCES pagos(id)
        );

        CREATE TABLE IF NOT EXISTS plan_pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pago_id INTEGER NOT NULL,
            monto_total REAL NOT NULL,
            interes_pct REAL DEFAULT 0,
            monto_con_interes REAL NOT NULL,
            num_cuotas INTEGER NOT NULL,
            monto_cuota REAL NOT NULL,
            frecuencia TEXT NOT NULL,
            fecha_inicio TEXT NOT NULL,
            estado TEXT DEFAULT 'activo',
            notas TEXT,
            fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pago_id) REFERENCES pagos(id)
        );

        CREATE TABLE IF NOT EXISTS cuotas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            numero INTEGER NOT NULL,
            fecha_vencimiento TEXT NOT NULL,
            monto REAL NOT NULL,
            fecha_pago TEXT,
            metodo_pago TEXT,
            estado TEXT DEFAULT 'pendiente',
            notas TEXT,
            FOREIGN KEY (plan_id) REFERENCES plan_pagos(id)
        );

        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            nombre TEXT,
            rol TEXT DEFAULT 'empleado',
            activo INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS cortes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            usuario_id INTEGER,
            total_efectivo REAL DEFAULT 0,
            total_tarjeta REAL DEFAULT 0,
            total_transferencia REAL DEFAULT 0,
            total_credito REAL DEFAULT 0,
            total_general REAL DEFAULT 0,
            num_pacientes INTEGER DEFAULT 0,
            citas_completadas INTEGER DEFAULT 0,
            citas_canceladas INTEGER DEFAULT 0,
            notas TEXT,
            fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS bitacora (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            accion TEXT NOT NULL,
            detalle TEXT,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            fecha TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT,
            numero_turno INTEGER DEFAULT 1,
            total_efectivo REAL DEFAULT 0,
            total_tarjeta REAL DEFAULT 0,
            total_transferencia REAL DEFAULT 0,
            total_credito REAL DEFAULT 0,
            total_general REAL DEFAULT 0,
            num_cobros INTEGER DEFAULT 0,
            num_cancelados INTEGER DEFAULT 0,
            estado TEXT DEFAULT 'abierto',
            notas TEXT,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        );

        CREATE TABLE IF NOT EXISTS periodontograma (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            dentista TEXT,
            tipo_denticion TEXT DEFAULT 'permanente',
            datos_json TEXT,
            notas TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id)
        );
    """)

    conn.commit()
    conn.close()


# ── PACIENTES CRUD ──────────────────────────────────────────────────────────

def crear_paciente(datos: dict) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pacientes
            (nombre, apellido, fecha_nacimiento, genero, telefono, email,
             direccion, numero_seguro, alergias, notas)
        VALUES
            (:nombre, :apellido, :fecha_nacimiento, :genero, :telefono, :email,
             :direccion, :numero_seguro, :alergias, :notas)
    """, datos)
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def obtener_pacientes(busqueda: str = "") -> list:
    conn = get_connection()
    cursor = conn.cursor()
    if busqueda:
        like = f"%{busqueda}%"
        cursor.execute("""
            SELECT * FROM pacientes
            WHERE activo = 1
              AND (nombre LIKE ? OR apellido LIKE ? OR telefono LIKE ? OR email LIKE ?)
            ORDER BY apellido, nombre
        """, (like, like, like, like))
    else:
        cursor.execute(
            "SELECT * FROM pacientes WHERE activo = 1 ORDER BY apellido, nombre"
        )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def obtener_paciente_por_id(paciente_id: int) -> dict | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pacientes WHERE id = ?", (paciente_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def actualizar_paciente(paciente_id: int, datos: dict):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE pacientes SET
            nombre = :nombre, apellido = :apellido,
            fecha_nacimiento = :fecha_nacimiento, genero = :genero,
            telefono = :telefono, email = :email,
            direccion = :direccion, numero_seguro = :numero_seguro,
            alergias = :alergias, notas = :notas
        WHERE id = :id
    """, {**datos, "id": paciente_id})
    conn.commit()
    conn.close()


def eliminar_paciente(paciente_id: int):
    """Soft delete — keeps data, marks as inactive."""
    conn = get_connection()
    conn.execute(
        "UPDATE pacientes SET activo = 0 WHERE id = ?", (paciente_id,)
    )
    conn.commit()
    conn.close()


# ── PERIODONTOGRAMA CRUD ────────────────────────────────────────────────────

def get_periodontogramas(paciente_id: int) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM periodontograma 
        WHERE paciente_id=? ORDER BY fecha DESC
    """, (paciente_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_periodontograma(pid: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM periodontograma WHERE id=?", (pid,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else {}


def crear_periodontograma(paciente_id: int, fecha: str, dentista: str,
                          tipo_denticion: str, datos_json: str, notas: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO periodontograma 
        (paciente_id, fecha, dentista, tipo_denticion, datos_json, notas)
        VALUES (?,?,?,?,?,?)
    """, (paciente_id, fecha, dentista, tipo_denticion, datos_json, notas))
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid


def actualizar_periodontograma(pid: int, datos_json: str, notas: str, dentista: str):
    conn = get_connection()
    conn.execute("""
        UPDATE periodontograma 
        SET datos_json=?, notas=?, dentista=?
        WHERE id=?
    """, (datos_json, notas, dentista, pid))
    conn.commit()
    conn.close()


def eliminar_periodontograma(pid: int):
    conn = get_connection()
    conn.execute("DELETE FROM periodontograma WHERE id=?", (pid,))
    conn.commit()
    conn.close()
