"""
corte.py
Módulo de Corte de Caja con autenticación por usuario/contraseña y exportación a PDF.
"""

import hashlib
import os
import sys
from datetime import datetime, date, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialog, QMessageBox, QFrame, QScrollArea,
    QFormLayout, QComboBox, QTextEdit, QFileDialog, QTableWidget,
    QTableWidgetItem, QHeaderView, QGridLayout
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QBrush, QColor

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database.db_manager import get_connection

# ── Palette ──────────────────────────────────────────────────────────────────
PRIMARY   = "#1A6B8A"
SECONDARY = "#2196B0"
ACCENT    = "#4ECDC4"
BG        = "#F5F8FA"
CARD      = "#FFFFFF"
TEXT      = "#2C3E50"
MUTED     = "#7F8C8D"
DANGER    = "#E74C3C"
SUCCESS   = "#27AE60"
WARNING   = "#F39C12"
BORDER    = "#DEE4E8"

_MESES = ["","enero","febrero","marzo","abril","mayo","junio",
          "julio","agosto","septiembre","octubre","noviembre","diciembre"]
_DIAS  = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]


def _btn(label, color, hover, text_color="white", w=None):
    b = QPushButton(label)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if w: b.setFixedWidth(w)
    b.setStyleSheet(f"""
        QPushButton {{
            background:{color}; color:{text_color};
            border:none; border-radius:8px;
            padding:9px 20px; font-size:13px; font-weight:600;
        }}
        QPushButton:hover {{ background:{hover}; }}
    """)
    return b


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── User CRUD ─────────────────────────────────────────────────────────────────
def init_admin():
    """Crea usuario admin por defecto si no existe ninguno."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM usuarios WHERE activo=1")
    if cur.fetchone()[0] == 0:
        conn.execute("""
            INSERT INTO usuarios (username, password_hash, nombre, rol)
            VALUES ('admin', ?, 'Administrador', 'admin')
        """, (_hash("admin123"),))
        conn.commit()
    conn.close()


def login(username: str, password: str) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM usuarios
        WHERE username=? AND password_hash=? AND activo=1
    """, (username, _hash(password)))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_usuarios() -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE activo=1 ORDER BY nombre")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def crear_usuario(username, password, nombre, rol):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO usuarios (username, password_hash, nombre, rol)
            VALUES (?,?,?,?)
        """, (username, _hash(password), nombre, rol))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def eliminar_usuario(uid: int):
    conn = get_connection()
    conn.execute("UPDATE usuarios SET activo=0 WHERE id=?", (uid,))
    conn.commit()
    conn.close()


# ── Corte CRUD ────────────────────────────────────────────────────────────────
def calcular_corte(fecha: str) -> dict:
    """Calcula los datos del corte para una fecha dada."""
    conn = get_connection()
    cur = conn.cursor()

    # Ingresos por método de pago
    cur.execute("""
        SELECT metodo_pago, SUM(monto_pagado) FROM pagos
        WHERE DATE(fecha)=? AND estado IN ('pagado','parcial')
        GROUP BY metodo_pago
    """, (fecha,))
    metodos = {row[0]: row[1] for row in cur.fetchall()}

    # Citas del día
    cur.execute("""
        SELECT estado, COUNT(*) FROM citas WHERE fecha=? GROUP BY estado
    """, (fecha,))
    citas_raw = {row[0]: row[1] for row in cur.fetchall()}

    # Pacientes únicos atendidos
    cur.execute("""
        SELECT COUNT(DISTINCT paciente_id) FROM citas
        WHERE fecha=? AND estado='completada'
    """, (fecha,))
    num_pac = cur.fetchone()[0] or 0

    # Cobros eliminados del día (bitácora)
    cur.execute("""
        SELECT COUNT(*) FROM bitacora
        WHERE accion = 'ELIMINAR_COBRO'
          AND DATE(fecha) = ?
    """, (fecha,))
    cobros_eliminados = cur.fetchone()[0] or 0

    # Comparativo últimos 7 días
    comparativo = []
    for i in range(6, -1, -1):
        d = (datetime.strptime(fecha, "%Y-%m-%d") - timedelta(days=i)).strftime("%Y-%m-%d")
        cur.execute("SELECT COALESCE(SUM(monto_pagado),0) FROM pagos WHERE DATE(fecha)=? AND estado IN ('pagado','parcial')", (d,))
        total = cur.fetchone()[0]
        comparativo.append({"fecha": d, "total": total})

    conn.close()

    total_efectivo     = metodos.get("Efectivo", 0) or 0
    total_tarjeta      = metodos.get("Tarjeta", 0) or 0
    total_transferencia= metodos.get("Transferencia", 0) or 0
    total_credito      = metodos.get("Crédito", 0) or 0
    total_general      = total_efectivo + total_tarjeta + total_transferencia + total_credito

    return {
        "fecha":              fecha,
        "total_efectivo":     total_efectivo,
        "total_tarjeta":      total_tarjeta,
        "total_transferencia":total_transferencia,
        "total_credito":      total_credito,
        "total_general":      total_general,
        "num_pacientes":      num_pac,
        "citas_completadas":  citas_raw.get("completada", 0),
        "citas_canceladas":   citas_raw.get("cancelada", 0),
        "cobros_eliminados":  cobros_eliminados,
        "comparativo":        comparativo,
    }


def guardar_corte(datos: dict, usuario_id: int, notas: str = ""):
    conn = get_connection()
    conn.execute("""
        INSERT INTO cortes
            (fecha, usuario_id, total_efectivo, total_tarjeta,
             total_transferencia, total_credito, total_general,
             num_pacientes, citas_completadas, citas_canceladas, notas)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
    """, (
        datos["fecha"], usuario_id,
        datos["total_efectivo"], datos["total_tarjeta"],
        datos["total_transferencia"], datos["total_credito"],
        datos["total_general"], datos["num_pacientes"],
        datos["citas_completadas"], datos["citas_canceladas"],
        notas
    ))
    conn.commit()
    conn.close()


def historial_cortes() -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.*, u.nombre as usuario_nombre
        FROM cortes c LEFT JOIN usuarios u ON c.usuario_id = u.id
        ORDER BY c.fecha DESC LIMIT 30
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ── Turnos ────────────────────────────────────────────────────────────────────
def turno_activo() -> dict | None:
    """Retorna el turno actualmente abierto, o None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.*, u.nombre as usuario_nombre
        FROM turnos t LEFT JOIN usuarios u ON t.usuario_id = u.id
        WHERE t.estado = 'abierto'
        ORDER BY t.id DESC LIMIT 1
    """)
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def iniciar_turno(usuario_id: int, numero_turno: int = 1) -> int:
    """Abre un nuevo turno. Retorna el ID del turno."""
    conn = get_connection()
    ahora = datetime.now()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO turnos (usuario_id, fecha, hora_inicio, numero_turno, estado)
        VALUES (?, ?, ?, ?, 'abierto')
    """, (usuario_id, ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M:%S"), numero_turno))
    turno_id = cur.lastrowid
    conn.commit()
    conn.close()
    return turno_id


def calcular_turno(turno_id: int) -> dict:
    """Calcula los totales del turno desde su hora_inicio hasta ahora."""
    conn = get_connection()
    cur = conn.cursor()

    # Obtener datos del turno
    cur.execute("SELECT * FROM turnos WHERE id=?", (turno_id,))
    turno = dict(cur.fetchone())

    fecha        = turno["fecha"]
    hora_inicio  = turno["hora_inicio"]
    hora_fin     = turno.get("hora_fin") or datetime.now().strftime("%H:%M:%S")
    dt_inicio    = f"{fecha} {hora_inicio}"
    dt_fin       = f"{fecha} {hora_fin}"
    num_turno    = turno["numero_turno"]

    # Cobros dentro del turno
    cur.execute("""
        SELECT metodo_pago, SUM(monto_pagado)
        FROM pagos
        WHERE fecha BETWEEN ? AND ?
          AND estado IN ('pagado','parcial')
        GROUP BY metodo_pago
    """, (dt_inicio, dt_fin))
    metodos = {row[0]: row[1] for row in cur.fetchall()}

    # Cancelaciones del turno — busca por número de turno en el detalle
    # Y también por rango de fechas como respaldo
    cur.execute("""
        SELECT COUNT(*) FROM bitacora
        WHERE accion = 'ELIMINAR_COBRO'
          AND (
              detalle LIKE ? 
              OR fecha BETWEEN ? AND ?
          )
    """, (f"[Turno #{num_turno}]%", dt_inicio, dt_fin))
    num_cancelados = cur.fetchone()[0] or 0

    # Número de cobros del turno
    cur.execute("""
        SELECT COUNT(*) FROM pagos
        WHERE fecha BETWEEN ? AND ?
          AND estado IN ('pagado','parcial')
    """, (dt_inicio, dt_fin))
    num_cobros = cur.fetchone()[0] or 0

    conn.close()

    total_efectivo      = metodos.get("Efectivo", 0) or 0
    total_tarjeta       = metodos.get("Tarjeta", 0) or 0
    total_transferencia = metodos.get("Transferencia", 0) or 0
    total_credito       = metodos.get("Crédito", 0) or 0
    total_general       = total_efectivo + total_tarjeta + total_transferencia + total_credito

    return {
        "turno_id":           turno_id,
        "numero_turno":       num_turno,
        "fecha":              fecha,
        "hora_inicio":        hora_inicio,
        "hora_fin":           hora_fin,
        "total_efectivo":     total_efectivo,
        "total_tarjeta":      total_tarjeta,
        "total_transferencia":total_transferencia,
        "total_credito":      total_credito,
        "total_general":      total_general,
        "num_cobros":         num_cobros,
        "num_cancelados":     num_cancelados,
    }


def cerrar_turno(turno_id: int, notas: str = "") -> dict:
    """Cierra el turno activo y guarda los totales."""
    datos = calcular_turno(turno_id)
    hora_fin = datetime.now().strftime("%H:%M:%S")
    conn = get_connection()
    conn.execute("""
        UPDATE turnos SET
            hora_fin=?, estado='cerrado',
            total_efectivo=?, total_tarjeta=?,
            total_transferencia=?, total_credito=?,
            total_general=?, num_cobros=?,
            num_cancelados=?, notas=?
        WHERE id=?
    """, (
        hora_fin,
        datos["total_efectivo"], datos["total_tarjeta"],
        datos["total_transferencia"], datos["total_credito"],
        datos["total_general"], datos["num_cobros"],
        datos["num_cancelados"], notas,
        turno_id
    ))
    conn.commit()
    conn.close()
    datos["hora_fin"] = hora_fin
    return datos


def historial_turnos(limite=20) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.*, u.nombre as usuario_nombre
        FROM turnos t LEFT JOIN usuarios u ON t.usuario_id = u.id
        ORDER BY t.id DESC LIMIT ?
    """, (limite,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ── Bitácora ──────────────────────────────────────────────────────────────────
def obtener_bitacora_completa(limite=100) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.*, u.nombre as usuario_nombre
        FROM bitacora b LEFT JOIN usuarios u ON b.usuario_id = u.id
        ORDER BY b.fecha DESC LIMIT ?
    """, (limite,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def registrar_en_bitacora(usuario_id: int, accion: str, detalle: str):
    fecha_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    conn.execute("""
        INSERT INTO bitacora (usuario_id, accion, detalle, fecha)
        VALUES (?,?,?,?)
    """, (usuario_id, accion, detalle, fecha_local))
    conn.commit()
    conn.close()


# ── PDF Export ────────────────────────────────────────────────────────────────
def exportar_pdf(datos: dict, usuario_nombre: str, notas: str, path: str):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     Table, TableStyle, HRFlowable)

    doc = SimpleDocTemplate(path, pagesize=letter,
                            leftMargin=0.8*inch, rightMargin=0.8*inch,
                            topMargin=0.8*inch, bottomMargin=0.8*inch)
    styles = getSampleStyleSheet()
    story  = []

    COLOR_PRIMARY = colors.HexColor("#1A6B8A")
    COLOR_ACCENT  = colors.HexColor("#4ECDC4")
    COLOR_MUTED   = colors.HexColor("#7F8C8D")
    COLOR_SUCCESS = colors.HexColor("#27AE60")
    COLOR_BG      = colors.HexColor("#F5F8FA")

    title_style = ParagraphStyle("title", fontSize=22, textColor=COLOR_PRIMARY,
                                  fontName="Helvetica-Bold", spaceAfter=4)
    sub_style   = ParagraphStyle("sub",   fontSize=11, textColor=COLOR_MUTED,
                                  fontName="Helvetica", spaceAfter=2)
    section_style = ParagraphStyle("section", fontSize=13, textColor=COLOR_PRIMARY,
                                    fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
    normal_style  = ParagraphStyle("normal", fontSize=10, textColor=colors.HexColor("#2C3E50"),
                                    fontName="Helvetica")

    # Header
    story.append(Paragraph("🦷 DentalApp — Corte de Caja", title_style))

    fecha_dt = datetime.strptime(datos["fecha"], "%Y-%m-%d")
    dia = _DIAS[fecha_dt.weekday()].capitalize()
    mes = _MESES[fecha_dt.month]
    fecha_str = f"{dia}, {fecha_dt.day} de {mes} de {fecha_dt.year}"
    story.append(Paragraph(fecha_str, sub_style))
    story.append(Paragraph(f"Generado por: {usuario_nombre}  |  {datetime.now().strftime('%H:%M hrs')}", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_PRIMARY, spaceAfter=12))

    # Total general destacado
    total_table = Table([[
        Paragraph("TOTAL DEL DÍA", ParagraphStyle("tt", fontSize=12, textColor=colors.white,
                   fontName="Helvetica-Bold", alignment=1)),
        Paragraph(f"${datos['total_general']:,.2f}", ParagraphStyle("tv", fontSize=18,
                   textColor=colors.white, fontName="Helvetica-Bold", alignment=1))
    ]], colWidths=[3*inch, 3.4*inch])
    total_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), COLOR_PRIMARY),
        ("ROUNDEDCORNERS", [8]),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LEFTPADDING",   (0,0), (-1,-1), 16),
        ("RIGHTPADDING",  (0,0), (-1,-1), 16),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 16))

    # Ingresos por método
    story.append(Paragraph("Ingresos por Método de Pago", section_style))
    metodos_data = [
        ["Método", "Monto"],
        ["💵 Efectivo",      f"${datos['total_efectivo']:,.2f}"],
        ["💳 Tarjeta",       f"${datos['total_tarjeta']:,.2f}"],
        ["🏦 Transferencia", f"${datos['total_transferencia']:,.2f}"],
        ["📋 Crédito",       f"${datos['total_credito']:,.2f}"],
    ]
    mt = Table(metodos_data, colWidths=[3.5*inch, 2.9*inch])
    mt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), COLOR_PRIMARY),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("BACKGROUND",    (0,1), (-1,-1), COLOR_BG),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, COLOR_BG]),
        ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor("#DEE4E8")),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("ALIGN",         (1,0), (1,-1), "RIGHT"),
    ]))
    story.append(mt)
    story.append(Spacer(1, 16))

    # Resumen de citas
    story.append(Paragraph("Resumen de Citas", section_style))
    citas_data = [
        ["Concepto", "Cantidad"],
        ["Pacientes atendidos",  str(datos["num_pacientes"])],
        ["Citas completadas",    str(datos["citas_completadas"])],
        ["Citas canceladas",     str(datos["citas_canceladas"])],
    ]
    ct = Table(citas_data, colWidths=[3.5*inch, 2.9*inch])
    ct.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), COLOR_ACCENT),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, COLOR_BG]),
        ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor("#DEE4E8")),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("ALIGN",         (1,0), (1,-1), "CENTER"),
    ]))
    story.append(ct)
    story.append(Spacer(1, 16))

    # Comparativo últimos 7 días
    story.append(Paragraph("Comparativo Ultimos 7 Dias", section_style))
    comp_header = [["Fecha", "Total"]]
    comp_rows = []
    for item in datos["comparativo"]:
        d = datetime.strptime(item["fecha"], "%Y-%m-%d")
        label = f"{_DIAS[d.weekday()].capitalize()} {d.day}/{d.month}"
        comp_rows.append([label, f"${item['total']:,.2f}"])
    comp_table = Table(comp_header + comp_rows, colWidths=[3.5*inch, 2.9*inch])
    comp_table.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), COLOR_PRIMARY),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, COLOR_BG]),
        ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor("#DEE4E8")),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("ALIGN",         (1,0), (1,-1), "RIGHT"),
    ]))
    story.append(comp_table)

    # Notas
    if notas.strip():
        story.append(Spacer(1, 16))
        story.append(Paragraph("Notas", section_style))
        story.append(Paragraph(notas, normal_style))

    # Footer
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_MUTED))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"DentalApp v1.0.0  —  Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M hrs')}",
        ParagraphStyle("footer", fontSize=8, textColor=COLOR_MUTED,
                       fontName="Helvetica", alignment=1)
    ))

    doc.build(story)


# ── Login Dialog ──────────────────────────────────────────────────────────────
class LoginCorteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Acceso — Corte de Caja")
        self.setFixedSize(380, 320)
        self.setStyleSheet(f"background: {BG};")
        self.usuario_logueado = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(90)
        header.setStyleSheet(f"background: {PRIMARY};")
        hl = QVBoxLayout(header)
        hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel("🔐  Corte de Caja")
        t.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        t.setStyleSheet("color: white;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(t)
        s = QLabel("Ingresa tus credenciales para continuar")
        s.setStyleSheet(f"color: #B2EBF2; font-size: 11px;")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(s)
        layout.addWidget(header)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(32, 24, 32, 24)
        bl.setSpacing(12)

        field_style = f"""
            QLineEdit {{
                border: 1.5px solid {BORDER}; border-radius: 8px;
                padding: 9px 12px; font-size: 13px;
                background: white; color: {TEXT};
            }}
            QLineEdit:focus {{ border-color: {SECONDARY}; }}
        """

        u_lbl = QLabel("Usuario:")
        u_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
        bl.addWidget(u_lbl)
        self.username = QLineEdit()
        self.username.setPlaceholderText("Ej. admin")
        self.username.setStyleSheet(field_style)
        bl.addWidget(self.username)

        p_lbl = QLabel("Contraseña:")
        p_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
        bl.addWidget(p_lbl)
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("••••••••")
        self.password.setStyleSheet(field_style)
        self.password.returnPressed.connect(self._login)
        bl.addWidget(self.password)

        btn = _btn("🔓  Entrar", PRIMARY, SECONDARY)
        btn.clicked.connect(self._login)
        bl.addWidget(btn)

        layout.addWidget(body)

    def _login(self):
        u = self.username.text().strip()
        p = self.password.text()
        if not u or not p:
            self._msg("Ingresa usuario y contraseña.")
            return
        user = login(u, p)
        if user:
            self.usuario_logueado = user
            self.accept()
        else:
            self._msg("❌ Usuario o contraseña incorrectos.")
            self.password.clear()

    def _msg(self, text):
        m = QMessageBox(self)
        m.setWindowTitle("Aviso")
        m.setText(text)
        m.setStyleSheet("color: black; background: white;")
        m.exec()


# ── Gestión de Usuarios Dialog ────────────────────────────────────────────────
class UsuariosDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestión de Usuarios")
        self.setMinimumSize(560, 420)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("👥  Usuarios del Sistema")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY};")
        layout.addWidget(title)

        # Form
        form_frame = QFrame()
        form_frame.setStyleSheet(f"background:{CARD}; border-radius:10px; border:1px solid {BORDER};")
        fl = QFormLayout(form_frame)
        fl.setContentsMargins(16, 14, 16, 14)
        fl.setSpacing(10)

        lbl = lambda t: QLabel(t) if True else None
        field_style = f"""
            QLineEdit {{
                border:1.5px solid {BORDER}; border-radius:6px;
                padding:7px 10px; font-size:13px; background:{BG}; color:{TEXT};
            }}
            QLineEdit:focus {{ border-color:{SECONDARY}; }}
        """
        combo_style = f"""
            QComboBox {{
                border:1.5px solid {BORDER}; border-radius:6px;
                padding:7px 10px; font-size:13px; background:{BG}; color:{TEXT};
            }}
            QComboBox QAbstractItemView {{ color:{TEXT}; background:white; }}
        """

        self.u_nombre   = QLineEdit(); self.u_nombre.setPlaceholderText("Nombre completo"); self.u_nombre.setStyleSheet(field_style)
        self.u_username = QLineEdit(); self.u_username.setPlaceholderText("Nombre de usuario"); self.u_username.setStyleSheet(field_style)
        self.u_password = QLineEdit(); self.u_password.setPlaceholderText("Contraseña"); self.u_password.setEchoMode(QLineEdit.EchoMode.Password); self.u_password.setStyleSheet(field_style)
        self.u_rol = QComboBox(); self.u_rol.addItems(["admin", "empleado"]); self.u_rol.setStyleSheet(combo_style)

        def lbl(t):
            l = QLabel(t); l.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:12px; border:none; background:transparent;")
            return l

        fl.addRow(lbl("Nombre:"),     self.u_nombre)
        fl.addRow(lbl("Usuario:"),    self.u_username)
        fl.addRow(lbl("Contraseña:"), self.u_password)
        fl.addRow(lbl("Rol:"),        self.u_rol)

        add_btn = _btn("➕  Agregar Usuario", SUCCESS, "#1E8449", w=200)
        add_btn.clicked.connect(self._agregar)
        fl.addRow("", add_btn)
        layout.addWidget(form_frame)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Nombre", "Usuario", "Rol"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setStyleSheet(f"""
            QTableWidget {{ background:{CARD}; border-radius:8px; border:1px solid {BORDER}; font-size:12px; }}
            QHeaderView::section {{ background:{PRIMARY}; color:white; padding:8px; font-weight:700; border:none; }}
            QTableWidget::item {{ padding:6px; color:{TEXT}; }}
        """)
        layout.addWidget(self.table)

    def _load(self):
        users = get_usuarios()
        self.table.setRowCount(len(users))
        for i, u in enumerate(users):
            for j, val in enumerate([str(u["id"]), u["nombre"], u["username"], u["rol"]]):
                self.table.setItem(i, j, QTableWidgetItem(val))

    def _agregar(self):
        nombre = self.u_nombre.text().strip()
        username = self.u_username.text().strip()
        password = self.u_password.text()
        rol = self.u_rol.currentText()
        if not nombre or not username or not password:
            m = QMessageBox(self); m.setWindowTitle("Error")
            m.setText("Todos los campos son obligatorios.")
            m.setStyleSheet("color:black; background:white;"); m.exec()
            return
        if crear_usuario(username, password, nombre, rol):
            self.u_nombre.clear(); self.u_username.clear(); self.u_password.clear()
            self._load()
            m = QMessageBox(self); m.setWindowTitle("Éxito")
            m.setText(f"Usuario '{username}' creado correctamente ✅")
            m.setStyleSheet("color:black; background:white;"); m.exec()
        else:
            m = QMessageBox(self); m.setWindowTitle("Error")
            m.setText("Ese nombre de usuario ya existe.")
            m.setStyleSheet("color:black; background:white;"); m.exec()


# ── Main corte widget ─────────────────────────────────────────────────────────
class CorteWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{BG};")
        self._usuario = None
        self._datos   = None
        init_admin()
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("💰  Corte de Caja")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        self.user_label = QLabel("🔒 Sin sesión")
        self.user_label.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        header.addWidget(self.user_label)

        login_btn = _btn("🔐  Iniciar Sesión", PRIMARY, SECONDARY)
        login_btn.clicked.connect(self._login)
        header.addWidget(login_btn)

        usuarios_btn = _btn("👥  Usuarios", "#8E44AD", "#7D3C98")
        usuarios_btn.clicked.connect(self._gestionar_usuarios)
        header.addWidget(usuarios_btn)
        root.addLayout(header)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{BORDER};"); sep.setFixedHeight(1)
        root.addWidget(sep)

        # Locked state
        self.locked_widget = QWidget()
        lw = QVBoxLayout(self.locked_widget)
        lw.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lock_icon = QLabel("🔒")
        lock_icon.setFont(QFont("Segoe UI", 52))
        lock_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lw.addWidget(lock_icon)
        lock_msg = QLabel("Inicia sesión para ver el corte de caja")
        lock_msg.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        lock_msg.setStyleSheet(f"color:{PRIMARY};")
        lock_msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lw.addWidget(lock_msg)
        lock_sub = QLabel("Solo usuarios autorizados pueden acceder a esta sección")
        lock_sub.setStyleSheet(f"color:{MUTED}; font-size:13px;")
        lock_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lw.addWidget(lock_sub)
        root.addWidget(self.locked_widget)

        # Content (hidden until login)
        self.content_widget = QWidget()
        self.content_widget.setVisible(False)
        cw = QVBoxLayout(self.content_widget)
        cw.setSpacing(16)

        # Date selector
        date_row = QHBoxLayout()
        date_lbl = QLabel("Fecha del corte:")
        date_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
        date_row.addWidget(date_lbl)

        self.fecha_input = QLineEdit()
        self.fecha_input.setText(date.today().strftime("%Y-%m-%d"))
        self.fecha_input.setFixedWidth(140)
        self.fecha_input.setStyleSheet(f"""
            QLineEdit {{
                border:1.5px solid {BORDER}; border-radius:8px;
                padding:8px 12px; font-size:13px; background:white; color:{TEXT};
            }}
        """)
        date_row.addWidget(self.fecha_input)

        calcular_btn = _btn("📊  Calcular Corte", PRIMARY, SECONDARY)
        calcular_btn.clicked.connect(self._calcular)
        date_row.addWidget(calcular_btn)
        date_row.addStretch()
        cw.addLayout(date_row)

        # Stats cards grid
        self.cards_widget = QWidget()
        self.cards_layout = QGridLayout(self.cards_widget)
        self.cards_layout.setSpacing(12)
        cw.addWidget(self.cards_widget)

        # Comparativo table
        comp_lbl = QLabel("📈  Comparativo últimos 7 días")
        comp_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        comp_lbl.setStyleSheet(f"color:{PRIMARY};")
        cw.addWidget(comp_lbl)

        self.comp_table = QTableWidget()
        self.comp_table.setColumnCount(2)
        self.comp_table.setHorizontalHeaderLabels(["Fecha", "Total del día"])
        self.comp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.comp_table.verticalHeader().setVisible(False)
        self.comp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.comp_table.setMaximumHeight(220)
        self.comp_table.setStyleSheet(f"""
            QTableWidget {{ background:{CARD}; border-radius:8px; border:1px solid {BORDER}; font-size:13px; }}
            QHeaderView::section {{ background:{PRIMARY}; color:white; padding:8px; font-weight:700; border:none; }}
            QTableWidget::item {{ padding:8px; color:{TEXT}; }}
            QTableWidget::item:alternate {{ background:#F8FBFC; }}
        """)
        self.comp_table.setAlternatingRowColors(True)
        cw.addWidget(self.comp_table)

        # Notas + actions
        notas_lbl = QLabel("Notas del corte:")
        notas_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
        cw.addWidget(notas_lbl)

        self.notas_input = QTextEdit()
        self.notas_input.setPlaceholderText("Observaciones, incidencias del día…")
        self.notas_input.setMaximumHeight(70)
        self.notas_input.setStyleSheet(f"""
            QTextEdit {{
                border:1.5px solid {BORDER}; border-radius:8px;
                padding:8px; font-size:13px; background:white; color:{TEXT};
            }}
        """)
        cw.addWidget(self.notas_input)

        actions = QHBoxLayout()
        guardar_btn = _btn("💾  Guardar Corte", SUCCESS, "#1E8449")
        guardar_btn.clicked.connect(self._guardar)
        pdf_btn = _btn("📄  Exportar PDF", "#8E44AD", "#7D3C98")
        pdf_btn.clicked.connect(self._exportar_pdf)
        actions.addWidget(guardar_btn)
        actions.addWidget(pdf_btn)
        actions.addStretch()
        cw.addLayout(actions)

        root.addWidget(self.content_widget)

    def _stat_card(self, icon, label, value, color):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background:{CARD}; border-radius:12px;
                border:1.5px solid {BORDER};
            }}
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(4)

        top = QHBoxLayout()
        ic = QLabel(icon)
        ic.setFont(QFont("Segoe UI", 20))
        ic.setStyleSheet("border:none; background:transparent;")
        top.addWidget(ic)
        top.addStretch()
        cl.addLayout(top)

        val_lbl = QLabel(value)
        val_lbl.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        val_lbl.setStyleSheet(f"color:{color}; border:none; background:transparent;")
        cl.addWidget(val_lbl)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color:{MUTED}; font-size:11px; border:none; background:transparent;")
        cl.addWidget(lbl)

        return card

    def _login(self):
        dlg = LoginCorteDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._usuario = dlg.usuario_logueado
            self.user_label.setText(f"✅ {self._usuario['nombre']} ({self._usuario['rol']})")
            self.locked_widget.setVisible(False)
            self.content_widget.setVisible(True)
            self._calcular()

    def _gestionar_usuarios(self):
        if not self._usuario or self._usuario.get("rol") != "admin":
            m = QMessageBox(self); m.setWindowTitle("Acceso denegado")
            m.setText("Solo el administrador puede gestionar usuarios.")
            m.setStyleSheet("color:black; background:white;"); m.exec()
            return
        UsuariosDialog(self).exec()

    def _calcular(self):
        fecha = self.fecha_input.text().strip()
        if not fecha:
            return
        try:
            datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            m = QMessageBox(self); m.setWindowTitle("Fecha inválida")
            m.setText("Usa el formato YYYY-MM-DD")
            m.setStyleSheet("color:black; background:white;"); m.exec()
            return

        self._datos = calcular_corte(fecha)

        # Clear old cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        d = self._datos
        cards = [
            ("💵", "Efectivo",      f"${d['total_efectivo']:,.2f}",      SUCCESS),
            ("💳", "Tarjeta",       f"${d['total_tarjeta']:,.2f}",       SECONDARY),
            ("🏦", "Transferencia", f"${d['total_transferencia']:,.2f}", WARNING),
            ("📋", "Crédito",       f"${d['total_credito']:,.2f}",       "#8E44AD"),
            ("🏆", "TOTAL GENERAL", f"${d['total_general']:,.2f}",       PRIMARY),
            ("👥", "Pacientes",     str(d["num_pacientes"]),              ACCENT),
            ("✅", "Citas completadas", str(d["citas_completadas"]),     SUCCESS),
            ("❌", "Citas canceladas",  str(d["citas_canceladas"]),      DANGER),
        ]
        for i, (icon, label, value, color) in enumerate(cards):
            card = self._stat_card(icon, label, value, color)
            self.cards_layout.addWidget(card, i // 4, i % 4)

        # Comparativo
        comp = d["comparativo"]
        self.comp_table.setRowCount(len(comp))
        hoy = date.today().strftime("%Y-%m-%d")
        for row, item in enumerate(comp):
            dt = datetime.strptime(item["fecha"], "%Y-%m-%d")
            dia = _DIAS[dt.weekday()].capitalize()
            fecha_display = f"{dia} {dt.day}/{dt.month}/{dt.year}"
            if item["fecha"] == fecha:
                fecha_display += "  ← hoy"

            fi = QTableWidgetItem(fecha_display)
            ti = QTableWidgetItem(f"${item['total']:,.2f}")
            ti.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            if item["fecha"] == fecha:
                for itm in [fi, ti]:
                    itm.setForeground(QBrush(QColor(PRIMARY)))
                    font = QFont(); font.setBold(True); itm.setFont(font)

            self.comp_table.setItem(row, 0, fi)
            self.comp_table.setItem(row, 1, ti)

        for r in range(self.comp_table.rowCount()):
            self.comp_table.setRowHeight(r, 36)

    def _guardar(self):
        if not self._datos or not self._usuario:
            return
        guardar_corte(self._datos, self._usuario["id"], self.notas_input.toPlainText())
        m = QMessageBox(self); m.setWindowTitle("Guardado")
        m.setText("✅ Corte guardado correctamente.")
        m.setStyleSheet("color:black; background:white;"); m.exec()

    def _exportar_pdf(self):
        if not self._datos or not self._usuario:
            m = QMessageBox(self); m.setWindowTitle("Aviso")
            m.setText("Primero calcula el corte del día.")
            m.setStyleSheet("color:black; background:white;"); m.exec()
            return

        fecha_str = self._datos["fecha"].replace("-", "")
        default_name = f"corte_{fecha_str}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF", default_name, "PDF (*.pdf)"
        )
        if not path:
            return

        try:
            exportar_pdf(
                self._datos,
                self._usuario["nombre"],
                self.notas_input.toPlainText(),
                path
            )
            m = QMessageBox(self); m.setWindowTitle("PDF Exportado")
            m.setText(f"✅ PDF guardado en:\n{path}")
            m.setStyleSheet("color:black; background:white;"); m.exec()
        except Exception as e:
            m = QMessageBox(self); m.setWindowTitle("Error")
            m.setText(f"No se pudo exportar el PDF:\n{str(e)}")
            m.setStyleSheet("color:black; background:white;"); m.exec()
