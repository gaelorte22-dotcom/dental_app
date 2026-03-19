"""
facturacion.py
Módulo de Facturación — Cobros, abonos, historial y corte de caja.
"""

import os, sys
from datetime import datetime, date, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialog, QMessageBox, QFrame, QTabWidget,
    QFormLayout, QComboBox, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QDoubleSpinBox, QScrollArea,
    QGridLayout, QFileDialog
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QBrush, QColor

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database.db_manager import get_connection, obtener_pacientes, obtener_paciente_por_id

# ── Palette ───────────────────────────────────────────────────────────────────
PRIMARY  = "#1A6B8A"
SECONDARY= "#2196B0"
ACCENT   = "#4ECDC4"
BG       = "#F5F8FA"
CARD     = "#FFFFFF"
TEXT     = "#2C3E50"
MUTED    = "#7F8C8D"
DANGER   = "#E74C3C"
SUCCESS  = "#27AE60"
WARNING  = "#F39C12"
BORDER   = "#DEE4E8"

_MESES = ["","enero","febrero","marzo","abril","mayo","junio",
          "julio","agosto","septiembre","octubre","noviembre","diciembre"]
_DIAS  = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]

METODOS = ["Efectivo", "Tarjeta", "Transferencia", "Crédito"]
ESTADOS = {"pagado": SUCCESS, "pendiente": WARNING, "parcial": SECONDARY}


def _btn(label, color, hover, text_color="white", w=None, h=None):
    b = QPushButton(label)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if w: b.setFixedWidth(w)
    if h: b.setFixedHeight(h)
    b.setStyleSheet(f"""
        QPushButton {{
            background:{color}; color:{text_color};
            border:none; border-radius:8px;
            padding:9px 20px; font-size:13px; font-weight:600;
        }}
        QPushButton:hover {{ background:{hover}; }}
    """)
    return b


def _field_style():
    return f"""
        QLineEdit, QDoubleSpinBox, QComboBox, QTextEdit {{
            border:1.5px solid {BORDER}; border-radius:8px;
            padding:8px 12px; font-size:13px;
            background:white; color:{TEXT};
        }}
        QLineEdit:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus {{
            border-color:{SECONDARY};
        }}
        QComboBox QAbstractItemView {{ color:{TEXT}; background:white; }}
    """


# ── DB helpers ────────────────────────────────────────────────────────────────
def crear_pago(datos: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pagos
            (paciente_id, fecha, concepto, monto_total, monto_pagado,
             metodo_pago, estado, notas)
        VALUES
            (:paciente_id, :fecha, :concepto, :monto_total, :monto_pagado,
             :metodo_pago, :estado, :notas)
    """, datos)
    conn.commit()
    pid = cur.lastrowid
    conn.close()
    return pid


def obtener_pagos(busqueda="", estado="", fecha_desde="", fecha_hasta="") -> list:
    conn = get_connection()
    cur = conn.cursor()
    q = """
        SELECT p.*, pa.nombre || ' ' || pa.apellido AS paciente_nombre
        FROM pagos p LEFT JOIN pacientes pa ON p.paciente_id = pa.id
        WHERE 1=1
    """
    params = []
    if busqueda:
        q += " AND (pa.nombre LIKE ? OR pa.apellido LIKE ? OR p.concepto LIKE ?)"
        like = f"%{busqueda}%"
        params += [like, like, like]
    if estado:
        q += " AND p.estado = ?"
        params.append(estado)
    if fecha_desde:
        q += " AND DATE(p.fecha) >= ?"
        params.append(fecha_desde)
    if fecha_hasta:
        q += " AND DATE(p.fecha) <= ?"
        params.append(fecha_hasta)
    q += " ORDER BY p.fecha DESC, p.id DESC"
    cur.execute(q, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def obtener_pagos_paciente(paciente_id: int) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM pagos WHERE paciente_id=?
        ORDER BY fecha DESC
    """, (paciente_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def obtener_pago_por_id(pago_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.*, pa.nombre || ' ' || pa.apellido AS paciente_nombre
        FROM pagos p LEFT JOIN pacientes pa ON p.paciente_id = pa.id
        WHERE p.id=?
    """, (pago_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def registrar_abono(pago_id: int, monto: float, metodo: str, notas: str = "") -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT monto_total, monto_pagado FROM pagos WHERE id=?", (pago_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False

    nuevo_pagado = row["monto_pagado"] + monto
    if nuevo_pagado > row["monto_total"]:
        conn.close()
        return False

    nuevo_estado = "pagado" if nuevo_pagado >= row["monto_total"] else "parcial"

    conn.execute("""
        INSERT INTO abonos (pago_id, monto, metodo_pago, notas)
        VALUES (?,?,?,?)
    """, (pago_id, monto, metodo, notas))
    conn.execute("""
        UPDATE pagos SET monto_pagado=?, estado=? WHERE id=?
    """, (nuevo_pagado, nuevo_estado, pago_id))
    conn.commit()
    conn.close()
    return True


def obtener_abonos(pago_id: int) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM abonos WHERE pago_id=? ORDER BY fecha", (pago_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def registrar_bitacora(usuario_id: int, accion: str, detalle: str):
    from datetime import datetime as _dt
    fecha_local = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    conn.execute("""
        INSERT INTO bitacora (usuario_id, accion, detalle, fecha)
        VALUES (?,?,?,?)
    """, (usuario_id, accion, detalle, fecha_local))
    conn.commit()
    conn.close()


def obtener_bitacora() -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT b.*, u.nombre AS usuario_nombre
        FROM bitacora b LEFT JOIN usuarios u ON b.usuario_id = u.id
        ORDER BY b.fecha DESC LIMIT 100
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def _get_turno_activo_id() -> str:
    """Retorna el número de turno activo o 'Sin turno'."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT numero_turno FROM turnos WHERE estado='abierto' ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return f"Turno #{row[0]}" if row else "Sin turno"


def eliminar_pago(pago_id: int, usuario_id: int, detalle: str):
    turno_info = _get_turno_activo_id()
    conn = get_connection()
    conn.execute("DELETE FROM abonos WHERE pago_id=?", (pago_id,))
    conn.execute("DELETE FROM cuotas WHERE plan_id IN (SELECT id FROM plan_pagos WHERE pago_id=?)", (pago_id,))
    conn.execute("DELETE FROM plan_pagos WHERE pago_id=?", (pago_id,))
    conn.execute("DELETE FROM pagos WHERE id=?", (pago_id,))
    conn.commit()
    conn.close()
    registrar_bitacora(usuario_id, "ELIMINAR_COBRO", f"[{turno_info}] {detalle}")


# ── New payment dialog ────────────────────────────────────────────────────────
class NuevoPagoDialog(QDialog):
    def __init__(self, parent=None, paciente_id=None):
        super().__init__(parent)
        self.setWindowTitle("Registrar Cobro")
        self.setMinimumWidth(500)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self._paciente_id = paciente_id
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        hdr = QWidget(); hdr.setFixedHeight(80)
        hdr.setStyleSheet(f"background:{PRIMARY};")
        hl = QVBoxLayout(hdr); hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel("💰  Registrar Cobro")
        t.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        t.setStyleSheet("color:white;")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(t)
        layout.addWidget(hdr)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 20, 28, 20)
        bl.setSpacing(12)

        fs = _field_style()

        # Paciente
        self.paciente_combo = QComboBox()
        self.paciente_combo.setStyleSheet(fs)
        self._pacientes = obtener_pacientes()
        self.paciente_combo.addItem("-- Seleccionar paciente --", None)
        sel_idx = 0
        for i, p in enumerate(self._pacientes):
            self.paciente_combo.addItem(f"{p['nombre']} {p['apellido']}", p["id"])
            if self._paciente_id and p["id"] == self._paciente_id:
                sel_idx = i + 1
        self.paciente_combo.setCurrentIndex(sel_idx)

        # Concepto
        self.concepto = QLineEdit()
        self.concepto.setPlaceholderText("Ej. Limpieza dental, extracción molar…")
        self.concepto.setStyleSheet(fs)

        # Monto total
        self.monto_total = QDoubleSpinBox()
        self.monto_total.setRange(0, 999999)
        self.monto_total.setPrefix("$ ")
        self.monto_total.setDecimals(2)
        self.monto_total.setSingleStep(50)
        self.monto_total.setStyleSheet(fs)
        self.monto_total.valueChanged.connect(self._sync_pago_inicial)

        # Tipo de pago
        self.tipo_pago = QComboBox()
        self.tipo_pago.addItems(["Pago completo", "Pago a plazos (abonos)"])
        self.tipo_pago.setStyleSheet(fs)
        self.tipo_pago.currentIndexChanged.connect(self._toggle_abono)

        # Pago inicial
        self.lbl_inicial = QLabel("Pago inicial:")
        self.lbl_inicial.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
        self.monto_inicial = QDoubleSpinBox()
        self.monto_inicial.setRange(0, 999999)
        self.monto_inicial.setPrefix("$ ")
        self.monto_inicial.setDecimals(2)
        self.monto_inicial.setSingleStep(50)
        self.monto_inicial.setStyleSheet(fs)
        self.lbl_inicial.setVisible(False)
        self.monto_inicial.setVisible(False)

        # Método
        self.metodo = QComboBox()
        self.metodo.addItems(METODOS)
        self.metodo.setStyleSheet(fs)

        # Fecha
        self.fecha = QLineEdit()
        self.fecha.setText(date.today().strftime("%Y-%m-%d"))
        self.fecha.setStyleSheet(fs)

        # Notas
        self.notas = QTextEdit()
        self.notas.setPlaceholderText("Observaciones…")
        self.notas.setMaximumHeight(60)
        self.notas.setStyleSheet(fs)

        def lbl(t):
            l = QLabel(t)
            l.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
            return l

        form = QFormLayout(); form.setSpacing(10)
        form.addRow(lbl("Paciente *"),    self.paciente_combo)
        form.addRow(lbl("Concepto *"),    self.concepto)
        form.addRow(lbl("Monto total *"), self.monto_total)
        form.addRow(lbl("Tipo de pago"),  self.tipo_pago)
        form.addRow(self.lbl_inicial,     self.monto_inicial)
        form.addRow(lbl("Método *"),      self.metodo)
        form.addRow(lbl("Fecha"),         self.fecha)
        form.addRow(lbl("Notas"),         self.notas)
        bl.addLayout(form)

        # Saldo info
        self.saldo_lbl = QLabel()
        self.saldo_lbl.setStyleSheet(f"color:{SECONDARY}; font-size:12px; font-weight:600;")
        bl.addWidget(self.saldo_lbl)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = _btn("Cancelar", "#ECF0F1", "#D5DBDB", TEXT)
        cancel.clicked.connect(self.reject)
        save = _btn("💾  Registrar Cobro", PRIMARY, SECONDARY)
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel); btn_row.addWidget(save)
        bl.addLayout(btn_row)
        layout.addWidget(body)

    def _sync_pago_inicial(self, val):
        self.monto_inicial.setMaximum(val)
        if self.tipo_pago.currentIndex() == 0:
            self.monto_inicial.setValue(val)
        self._update_saldo()

    def _toggle_abono(self, idx):
        es_plazo = idx == 1
        self.lbl_inicial.setVisible(es_plazo)
        self.monto_inicial.setVisible(es_plazo)
        if not es_plazo:
            self.monto_inicial.setValue(self.monto_total.value())
        self._update_saldo()

    def _update_saldo(self):
        total = self.monto_total.value()
        inicial = self.monto_inicial.value() if self.tipo_pago.currentIndex() == 1 else total
        pendiente = total - inicial
        if pendiente > 0:
            self.saldo_lbl.setText(f"💳 Saldo pendiente: ${pendiente:,.2f}")
        else:
            self.saldo_lbl.setText("")

    def _save(self):
        if self.paciente_combo.currentData() is None:
            self._msg("Selecciona un paciente.")
            return
        if not self.concepto.text().strip():
            self._msg("El concepto es obligatorio.")
            return
        if self.monto_total.value() <= 0:
            self._msg("El monto debe ser mayor a $0.")
            return

        es_plazo = self.tipo_pago.currentIndex() == 1
        monto_pagado = self.monto_inicial.value() if es_plazo else self.monto_total.value()

        if monto_pagado > self.monto_total.value():
            self._msg("El pago inicial no puede ser mayor al total.")
            return

        if monto_pagado >= self.monto_total.value():
            estado = "pagado"
        elif monto_pagado > 0:
            estado = "parcial"
        else:
            estado = "pendiente"

        self.result_data = {
            "paciente_id":  self.paciente_combo.currentData(),
            "fecha":        self.fecha.text().strip(),
            "concepto":     self.concepto.text().strip(),
            "monto_total":  self.monto_total.value(),
            "monto_pagado": monto_pagado,
            "metodo_pago":  self.metodo.currentText(),
            "estado":       estado,
            "notas":        self.notas.toPlainText().strip(),
        }
        self.accept()

    def _msg(self, txt):
        m = QMessageBox(self); m.setWindowTitle("Aviso")
        m.setText(txt); m.setStyleSheet("color:black; background:white;")
        m.exec()


# ── Abono dialog ──────────────────────────────────────────────────────────────
class AbonoDialog(QDialog):
    def __init__(self, pago: dict, parent=None):
        super().__init__(parent)
        self.pago = pago
        self.setWindowTitle(f"Registrar Abono — {pago.get('paciente_nombre','')}")
        self.setMinimumWidth(440)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel("💳  Registrar Abono")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY};")
        layout.addWidget(title)

        # Info card
        pendiente = self.pago["monto_total"] - self.pago["monto_pagado"]
        info = QFrame()
        info.setStyleSheet(f"background:{CARD}; border-radius:8px; border:1px solid {BORDER};")
        il = QVBoxLayout(info); il.setContentsMargins(14,10,14,10); il.setSpacing(4)
        for lbl_txt, val in [
            ("Concepto:", self.pago.get("concepto","—")),
            ("Total:",    f"${self.pago['monto_total']:,.2f}"),
            ("Pagado:",   f"${self.pago['monto_pagado']:,.2f}"),
            ("Pendiente:",f"${pendiente:,.2f}"),
        ]:
            row = QHBoxLayout()
            l = QLabel(lbl_txt); l.setStyleSheet(f"color:{MUTED}; font-size:12px; border:none; background:transparent;")
            v = QLabel(val);     v.setStyleSheet(f"color:{TEXT}; font-size:12px; font-weight:600; border:none; background:transparent;")
            row.addWidget(l); row.addWidget(v); row.addStretch()
            il.addLayout(row)
        layout.addWidget(info)

        fs = _field_style()

        self.monto = QDoubleSpinBox()
        self.monto.setRange(0.01, pendiente)
        self.monto.setPrefix("$ ")
        self.monto.setDecimals(2)
        self.monto.setValue(pendiente)
        self.monto.setStyleSheet(fs)

        self.metodo = QComboBox()
        self.metodo.addItems(METODOS)
        self.metodo.setStyleSheet(fs)

        self.notas = QLineEdit()
        self.notas.setPlaceholderText("Observaciones…")
        self.notas.setStyleSheet(fs)

        form = QFormLayout(); form.setSpacing(10)
        def lbl(t):
            l = QLabel(t); l.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
            return l
        form.addRow(lbl("Monto abono *"), self.monto)
        form.addRow(lbl("Método *"),      self.metodo)
        form.addRow(lbl("Notas"),         self.notas)
        layout.addLayout(form)

        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = _btn("Cancelar", "#ECF0F1", "#D5DBDB", TEXT)
        cancel.clicked.connect(self.reject)
        save = _btn("💾  Registrar Abono", SUCCESS, "#1E8449")
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel); btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _save(self):
        self.result = {
            "monto":  self.monto.value(),
            "metodo": self.metodo.currentText(),
            "notas":  self.notas.text().strip(),
        }
        self.accept()


# ── Detalle pago dialog ───────────────────────────────────────────────────────
class DetallePagoDialog(QDialog):
    def __init__(self, pago: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Detalle — {pago.get('paciente_nombre','')}")
        self.setMinimumWidth(500)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self._build(pago)

    def _build(self, p):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel(f"🧾  {p.get('concepto','—')}")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY};")
        layout.addWidget(title)

        pendiente = p["monto_total"] - p["monto_pagado"]
        estado_color = ESTADOS.get(p.get("estado","pagado"), SUCCESS)

        info = QFrame()
        info.setStyleSheet(f"background:{CARD}; border-radius:10px; border:1px solid {BORDER};")
        il = QGridLayout(info); il.setContentsMargins(16,14,16,14); il.setSpacing(8)

        fields = [
            ("Paciente",   p.get("paciente_nombre","—")),
            ("Fecha",      p.get("fecha","—")[:10]),
            ("Total",      f"${p['monto_total']:,.2f}"),
            ("Pagado",     f"${p['monto_pagado']:,.2f}"),
            ("Pendiente",  f"${pendiente:,.2f}"),
            ("Método",     p.get("metodo_pago","—")),
            ("Estado",     p.get("estado","—").capitalize()),
            ("Notas",      p.get("notas","—") or "—"),
        ]
        for i, (k, v) in enumerate(fields):
            lk = QLabel(k+":"); lk.setStyleSheet(f"color:{MUTED}; font-size:12px; border:none; background:transparent;")
            lv = QLabel(v);     lv.setStyleSheet(f"color:{TEXT}; font-size:12px; font-weight:600; border:none; background:transparent; padding:0;")
            if k == "Estado":
                lv.setStyleSheet(f"color:{estado_color}; font-size:12px; font-weight:700; border:none; background:transparent;")
            il.addWidget(lk, i, 0)
            il.addWidget(lv, i, 1)
        layout.addWidget(info)

        # Abonos table
        abonos = obtener_abonos(p["id"])
        if abonos:
            ab_lbl = QLabel("Historial de Abonos:")
            ab_lbl.setStyleSheet(f"color:{TEXT}; font-weight:700; font-size:13px;")
            layout.addWidget(ab_lbl)

            ab_table = QTableWidget(len(abonos), 3)
            ab_table.setHorizontalHeaderLabels(["Fecha", "Método", "Monto"])
            ab_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            ab_table.verticalHeader().setVisible(False)
            ab_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            ab_table.setMaximumHeight(140)
            ab_table.setStyleSheet(f"""
                QTableWidget {{ background:{CARD}; border-radius:8px; border:1px solid {BORDER}; font-size:12px; }}
                QHeaderView::section {{ background:{PRIMARY}; color:white; padding:6px; font-weight:700; border:none; }}
                QTableWidget::item {{ padding:6px; color:{TEXT}; }}
            """)
            for i, ab in enumerate(abonos):
                ab_table.setItem(i, 0, QTableWidgetItem(ab["fecha"][:10]))
                ab_table.setItem(i, 1, QTableWidgetItem(ab.get("metodo_pago","—")))
                monto_item = QTableWidgetItem(f"${ab['monto']:,.2f}")
                monto_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                ab_table.setItem(i, 2, monto_item)
            layout.addWidget(ab_table)

        close = _btn("Cerrar", PRIMARY, SECONDARY)
        close.clicked.connect(self.accept)
        layout.addWidget(close)


# ── Corte tab (lógica inline, sin importar CorteWidget) ──────────────────────
import hashlib as _hashlib
from modules.corte import (calcular_corte, guardar_corte,
                            exportar_pdf, init_admin, login,
                            turno_activo, iniciar_turno, calcular_turno,
                            cerrar_turno, historial_turnos,
                            obtener_bitacora_completa, registrar_en_bitacora)
from modules.plan_pagos import (CalculadoraPlanDialog, DetallePlanWidget,
                                 crear_plan, obtener_cuotas_proximas)


# ── Admin auth dialog ─────────────────────────────────────────────────────────
class AdminAuthDialog(QDialog):
    """Pide contraseña de admin para acciones sensibles."""
    def __init__(self, parent=None, accion="esta acción"):
        super().__init__(parent)
        self.setWindowTitle("Autenticación Requerida")
        self.setFixedWidth(380)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self.usuario_autenticado = None
        self._accion = accion
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)

        hdr = QWidget(); hdr.setFixedHeight(80)
        hdr.setStyleSheet(f"background:{DANGER};")
        hl = QVBoxLayout(hdr); hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel("🔐  Acción Protegida")
        t.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        t.setStyleSheet("color:white;"); t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(t)
        s = QLabel(f"Se requiere contraseña de admin para {self._accion}")
        s.setStyleSheet("color:#FFCDD2; font-size:11px;")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(s)
        layout.addWidget(hdr)

        body = QWidget()
        bl = QVBoxLayout(body); bl.setContentsMargins(28,20,28,20); bl.setSpacing(12)

        fs = f"""
            QLineEdit {{
                border:1.5px solid {BORDER}; border-radius:8px;
                padding:9px 12px; font-size:13px; background:white; color:{TEXT};
            }}
            QLineEdit:focus {{ border-color:{DANGER}; }}
        """

        def lbl(t):
            l = QLabel(t); l.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
            return l

        self.username = QLineEdit()
        self.username.setPlaceholderText("Usuario admin")
        self.username.setStyleSheet(fs)
        bl.addWidget(lbl("Usuario:")); bl.addWidget(self.username)

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Contraseña")
        self.password.setStyleSheet(fs)
        self.password.returnPressed.connect(self._auth)
        bl.addWidget(lbl("Contraseña:")); bl.addWidget(self.password)

        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = _btn("Cancelar", "#ECF0F1", "#D5DBDB", TEXT)
        cancel.clicked.connect(self.reject)
        confirm = _btn("🔓  Confirmar", DANGER, "#C0392B")
        confirm.clicked.connect(self._auth)
        btn_row.addWidget(cancel); btn_row.addWidget(confirm)
        bl.addLayout(btn_row)
        layout.addWidget(body)

    def _auth(self):
        from modules.corte import login
        u = self.username.text().strip()
        p = self.password.text()
        user = login(u, p)
        if user and user.get("rol") == "admin":
            self.usuario_autenticado = user
            self.accept()
        else:
            m = QMessageBox(self); m.setWindowTitle("Error")
            m.setText("❌ Credenciales incorrectas o sin permisos de admin.")
            m.setStyleSheet("color:black; background:white;"); m.exec()
            self.password.clear()


# ── Main Facturación widget ───────────────────────────────────────────────────
class FacturacionWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{BG};")
        init_admin()
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("💰  Facturación")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY};")
        header.addWidget(title)
        header.addStretch()
        root.addLayout(header)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{BORDER};"); sep.setFixedHeight(1)
        root.addWidget(sep)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border:1px solid {BORDER}; border-radius:8px;
                background:{CARD};
            }}
            QTabBar::tab {{
                background:{BG}; color:{MUTED};
                padding:10px 22px; font-size:13px; font-weight:600;
                border:1px solid {BORDER}; border-bottom:none;
                border-top-left-radius:8px; border-top-right-radius:8px;
                margin-right:4px;
            }}
            QTabBar::tab:selected {{
                background:{CARD}; color:{PRIMARY};
                border-bottom:2px solid {PRIMARY};
            }}
            QTabBar::tab:hover {{ background:white; color:{TEXT}; }}
        """)

        self.tabs.addTab(self._build_cobros_tab(), "📋  Cobros")
        self.tabs.addTab(self._build_pendientes_tab(), "⏳  Pendientes / Abonos")
        self.tabs.addTab(self._build_corte_tab(), "📊  Corte de Caja")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self.tabs)

    def _on_tab_changed(self, index):
        # Cerrar sesión del corte al salir de esa pestaña (índice 2)
        if index != 2 and self._corte_usuario is not None:
            self._corte_logout()

    # ── TAB 1: Cobros ─────────────────────────────────────────────────────────
    def _build_cobros_tab(self):
        w = QWidget(); w.setStyleSheet(f"background:{CARD};")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Subtabs: Hoy e Historial
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border:none; background:transparent; }}
            QTabBar::tab {{
                background:#ECF0F1; color:{MUTED};
                padding:7px 18px; font-size:12px; font-weight:600;
                border-radius:6px; margin-right:4px;
            }}
            QTabBar::tab:selected {{ background:{PRIMARY}; color:white; }}
            QTabBar::tab:hover {{ background:{SECONDARY}; color:white; }}
        """)
        self.sub_tabs.addTab(self._build_hoy_tab(), "📋  Cobros de Hoy")
        self.sub_tabs.addTab(self._build_historial_tab(), "🗂  Historial")
        layout.addWidget(self.sub_tabs)
        return w

    def _build_hoy_tab(self):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        top = QHBoxLayout()
        hoy_lbl = QLabel(f"📅  {date.today().strftime('%d/%m/%Y')}")
        hoy_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        hoy_lbl.setStyleSheet(f"color:{PRIMARY};")
        top.addWidget(hoy_lbl)

        self.search_hoy = QLineEdit()
        self.search_hoy.setPlaceholderText("🔍  Buscar paciente o concepto…")
        self.search_hoy.setStyleSheet(f"""
            QLineEdit {{
                border:1.5px solid {BORDER}; border-radius:20px;
                padding:7px 14px; font-size:13px; background:white; color:{TEXT};
            }}
            QLineEdit:focus {{ border-color:{SECONDARY}; }}
        """)
        self.search_hoy.textChanged.connect(self._load_hoy)
        top.addWidget(self.search_hoy)

        refresh_btn = _btn("🔄", "#ECF0F1", "#D5DBDB", TEXT, w=42)
        refresh_btn.clicked.connect(self._load_hoy)
        top.addWidget(refresh_btn)

        nuevo_btn = _btn("＋  Nuevo Cobro", PRIMARY, SECONDARY)
        nuevo_btn.clicked.connect(self._nuevo_cobro)
        top.addWidget(nuevo_btn)
        layout.addLayout(top)

        self.stats_hoy = QLabel()
        self.stats_hoy.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        layout.addWidget(self.stats_hoy)

        self.tabla_hoy = self._make_table(
            ["ID", "Paciente", "Concepto", "Total", "Pagado", "Pendiente", "Estado", "Acciones"]
        )
        layout.addWidget(self.tabla_hoy)
        self._load_hoy()
        return w

    def _build_historial_tab(self):
        w = QWidget(); w.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(10)

        # Filtros
        filtros = QHBoxLayout()
        field_style = f"""
            QLineEdit {{
                border:1.5px solid {BORDER}; border-radius:8px;
                padding:7px 12px; font-size:13px; background:white; color:{TEXT};
            }}
            QLineEdit:focus {{ border-color:{SECONDARY}; }}
        """

        desde_lbl = QLabel("Desde:")
        desde_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
        filtros.addWidget(desde_lbl)
        self.hist_desde = QLineEdit()
        self.hist_desde.setPlaceholderText("YYYY-MM-DD")
        self.hist_desde.setFixedWidth(120)
        self.hist_desde.setStyleSheet(field_style)
        # Default: 30 días atrás
        self.hist_desde.setText((date.today() - timedelta(days=30)).strftime("%Y-%m-%d"))
        filtros.addWidget(self.hist_desde)

        hasta_lbl = QLabel("Hasta:")
        hasta_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
        filtros.addWidget(hasta_lbl)
        self.hist_hasta = QLineEdit()
        self.hist_hasta.setPlaceholderText("YYYY-MM-DD")
        self.hist_hasta.setFixedWidth(120)
        self.hist_hasta.setStyleSheet(field_style)
        self.hist_hasta.setText(date.today().strftime("%Y-%m-%d"))
        filtros.addWidget(self.hist_hasta)

        self.search_hist = QLineEdit()
        self.search_hist.setPlaceholderText("🔍  Buscar…")
        self.search_hist.setStyleSheet(f"""
            QLineEdit {{
                border:1.5px solid {BORDER}; border-radius:20px;
                padding:7px 14px; font-size:13px; background:white; color:{TEXT};
            }}
        """)
        filtros.addWidget(self.search_hist)

        self.filtro_estado_hist = QComboBox()
        self.filtro_estado_hist.addItems(["Todos", "pagado", "parcial", "pendiente"])
        self.filtro_estado_hist.setFixedWidth(120)
        self.filtro_estado_hist.setStyleSheet(f"""
            QComboBox {{
                border:1.5px solid {BORDER}; border-radius:8px;
                padding:7px 10px; font-size:13px; background:white; color:{TEXT};
            }}
            QComboBox QAbstractItemView {{ color:{TEXT}; background:white; }}
        """)
        filtros.addWidget(self.filtro_estado_hist)

        buscar_btn = _btn("🔍  Buscar", PRIMARY, SECONDARY)
        buscar_btn.clicked.connect(self._load_historial)
        filtros.addWidget(buscar_btn)
        layout.addLayout(filtros)

        self.stats_hist = QLabel()
        self.stats_hist.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        layout.addWidget(self.stats_hist)

        self.tabla_hist = self._make_table(
            ["ID", "Fecha", "Paciente", "Concepto", "Total", "Pagado", "Pendiente", "Estado", "Acciones"]
        )
        layout.addWidget(self.tabla_hist)
        self._load_historial()
        return w

    def _load_hoy(self):
        hoy = date.today().strftime("%Y-%m-%d")
        busqueda = self.search_hoy.text().strip()
        pagos = obtener_pagos(busqueda, fecha_desde=hoy, fecha_hasta=hoy)

        total_hoy = sum(p["monto_pagado"] for p in pagos)
        self.stats_hoy.setText(
            f"{len(pagos)} cobro(s) hoy  |  Total cobrado: ${total_hoy:,.2f}"
        )
        self._fill_tabla(self.tabla_hoy, pagos, show_fecha=False)

    def _load_historial(self):
        desde  = self.hist_desde.text().strip()
        hasta  = self.hist_hasta.text().strip()
        busqueda = self.search_hist.text().strip()
        estado_raw = self.filtro_estado_hist.currentText()
        estado = "" if estado_raw == "Todos" else estado_raw
        pagos = obtener_pagos(busqueda, estado, fecha_desde=desde, fecha_hasta=hasta)

        total = sum(p["monto_pagado"] for p in pagos)
        self.stats_hist.setText(
            f"{len(pagos)} registro(s)  |  Total: ${total:,.2f}"
        )
        self._fill_tabla(self.tabla_hist, pagos, show_fecha=True)

    def _load_cobros(self):
        self._load_hoy()

    def _fill_tabla(self, tabla, pagos, show_fecha=False):
        tabla.setRowCount(len(pagos))
        for row, p in enumerate(pagos):
            pendiente = p["monto_total"] - p["monto_pagado"]
            if show_fecha:
                vals = [
                    str(p["id"]),
                    p.get("fecha","")[:10],
                    p.get("paciente_nombre","—"),
                    p.get("concepto","—"),
                    f"${p['monto_total']:,.2f}",
                    f"${p['monto_pagado']:,.2f}",
                    f"${pendiente:,.2f}",
                    p.get("estado","—"),
                ]
                estado_col = 7
            else:
                vals = [
                    str(p["id"]),
                    p.get("paciente_nombre","—"),
                    p.get("concepto","—"),
                    f"${p['monto_total']:,.2f}",
                    f"${p['monto_pagado']:,.2f}",
                    f"${pendiente:,.2f}",
                    p.get("estado","—"),
                ]
                estado_col = 6

            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, p["id"])
                if col == estado_col:
                    color = ESTADOS.get(p.get("estado","pagado"), SUCCESS)
                    item.setForeground(QBrush(QColor(color)))
                    font = QFont(); font.setBold(True); item.setFont(font)
                tabla.setItem(row, col, item)

            accion_col = len(vals)
            cell = QWidget(); cell.setStyleSheet("background:transparent;")
            hb = QHBoxLayout(cell); hb.setContentsMargins(4,2,4,2); hb.setSpacing(4)

            ver_btn = _btn("👁", "#27AE60", "#1E8449")
            ver_btn.setFixedSize(34, 28)
            ver_btn.clicked.connect(lambda _, pid=p["id"]: self._ver_detalle(pid))

            del_btn = _btn("🗑", DANGER, "#C0392B")
            del_btn.setFixedSize(34, 28)
            del_btn.clicked.connect(lambda _, pid=p["id"]: self._eliminar_pago(pid))

            hb.addWidget(ver_btn); hb.addWidget(del_btn)
            tabla.setCellWidget(row, accion_col, cell)

        for r in range(tabla.rowCount()):
            tabla.setRowHeight(r, 42)

    # ── TAB 2: Pendientes / Abonos ────────────────────────────────────────────
    def _build_pendientes_tab(self):
        w = QWidget(); w.setStyleSheet(f"background:{CARD};")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # Próximas cuotas alert
        self.proximas_frame = QFrame()
        self.proximas_frame.setStyleSheet(f"background:#FFF8E1; border-radius:8px; border:1.5px solid {WARNING};")
        pfl = QVBoxLayout(self.proximas_frame); pfl.setContentsMargins(14,10,14,10); pfl.setSpacing(4)
        prox_title = QLabel("⚠️  Cuotas que vencen esta semana")
        prox_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        prox_title.setStyleSheet(f"color:{WARNING}; border:none; background:transparent;")
        pfl.addWidget(prox_title)
        self.proximas_lbl = QLabel()
        self.proximas_lbl.setStyleSheet(f"color:{TEXT}; font-size:12px; border:none; background:transparent;")
        self.proximas_lbl.setWordWrap(True)
        pfl.addWidget(self.proximas_lbl)
        layout.addWidget(self.proximas_frame)

        top = QHBoxLayout()
        lbl = QLabel("Pagos con saldo pendiente")
        lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color:{PRIMARY};")
        top.addWidget(lbl); top.addStretch()
        refresh_btn = _btn("🔄", "#ECF0F1", "#D5DBDB", TEXT, w=42)
        refresh_btn.clicked.connect(self._load_pendientes)
        top.addWidget(refresh_btn)
        layout.addLayout(top)

        self.stats_pendientes = QLabel()
        self.stats_pendientes.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        layout.addWidget(self.stats_pendientes)

        self.tabla_pendientes = self._make_table(
            ["ID", "Paciente", "Concepto", "Total", "Pagado", "Pendiente", "Estado", "Acciones"]
        )
        layout.addWidget(self.tabla_pendientes)
        self._load_pendientes()
        return w

    def _load_pendientes(self):
        # Próximas cuotas
        proximas = obtener_cuotas_proximas(7)
        if proximas:
            lines = []
            for c in proximas[:5]:
                lines.append(f"• {c['paciente_nombre']} — {c['concepto']} — Cuota #{c['numero']} vence {c['fecha_vencimiento']} (${c['monto']:,.2f})")
            self.proximas_lbl.setText("\n".join(lines))
            self.proximas_frame.setVisible(True)
        else:
            self.proximas_frame.setVisible(False)

        pagos = obtener_pagos(estado="pendiente") + obtener_pagos(estado="parcial")
        pagos.sort(key=lambda x: x["fecha"], reverse=True)

        total_pendiente = sum(p["monto_total"] - p["monto_pagado"] for p in pagos)
        self.stats_pendientes.setText(
            f"{len(pagos)} cuenta(s) pendiente(s)  |  Total por cobrar: ${total_pendiente:,.2f}"
        )

        self.tabla_pendientes.setRowCount(len(pagos))
        for row, p in enumerate(pagos):
            pendiente = p["monto_total"] - p["monto_pagado"]
            vals = [
                str(p["id"]),
                p.get("paciente_nombre","—"),
                p.get("concepto","—"),
                f"${p['monto_total']:,.2f}",
                f"${p['monto_pagado']:,.2f}",
                f"${pendiente:,.2f}",
                p.get("estado","—"),
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if col == 6:
                    color = ESTADOS.get(p.get("estado","pagado"), SUCCESS)
                    item.setForeground(QBrush(QColor(color)))
                    font = QFont(); font.setBold(True); item.setFont(font)
                self.tabla_pendientes.setItem(row, col, item)

            cell = QWidget(); cell.setStyleSheet("background:transparent;")
            hb = QHBoxLayout(cell); hb.setContentsMargins(4,2,4,2); hb.setSpacing(4)

            abono_btn = _btn("💳 Abonar", SUCCESS, "#1E8449")
            abono_btn.setFixedHeight(28)
            abono_btn.clicked.connect(lambda _, pid=p["id"]: self._registrar_abono(pid))

            plan_btn = _btn("📅 Plan", SECONDARY, PRIMARY)
            plan_btn.setFixedHeight(28)
            plan_btn.clicked.connect(lambda _, pp=p: self._ver_plan(pp))

            hb.addWidget(abono_btn); hb.addWidget(plan_btn)
            self.tabla_pendientes.setCellWidget(row, 7, cell)

        for r in range(self.tabla_pendientes.rowCount()):
            self.tabla_pendientes.setRowHeight(r, 42)

    # ── TAB 3: Corte de Caja ──────────────────────────────────────────────────
    def _build_corte_tab(self):
        w = QWidget(); w.setStyleSheet(f"background:{CARD};")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        self._corte_usuario = None
        self._corte_datos   = None

        # Header row
        top = QHBoxLayout()
        self._corte_user_lbl = QLabel("🔒 Sin sesión")
        self._corte_user_lbl.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        top.addWidget(self._corte_user_lbl); top.addStretch()

        self._refresh_btn = _btn("🔄  Refrescar", SECONDARY, PRIMARY)
        self._refresh_btn.setVisible(False)
        self._refresh_btn.clicked.connect(self._corte_calcular)
        top.addWidget(self._refresh_btn)

        self._logout_btn = _btn("🔓  Cerrar Sesión", DANGER, "#C0392B")
        self._logout_btn.setVisible(False)
        self._logout_btn.clicked.connect(self._corte_logout)
        top.addWidget(self._logout_btn)

        self._login_btn = _btn("🔐  Iniciar Sesión", PRIMARY, SECONDARY)
        self._login_btn.clicked.connect(self._corte_login)
        top.addWidget(self._login_btn)
        layout.addLayout(top)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{BORDER};"); sep.setFixedHeight(1)
        layout.addWidget(sep)

        # Locked
        self._corte_locked = QWidget()
        ll = QVBoxLayout(self._corte_locked)
        ll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lock_icon = QLabel("🔒"); lock_icon.setFont(QFont("Segoe UI", 42))
        lock_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(lock_icon)
        lock_lbl = QLabel("Inicia sesión para ver el corte")
        lock_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        lock_lbl.setStyleSheet(f"color:{PRIMARY};")
        lock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(lock_lbl)
        layout.addWidget(self._corte_locked)

        # Content con subtabs
        self._corte_content = QWidget(); self._corte_content.setVisible(False)
        cl = QVBoxLayout(self._corte_content); cl.setSpacing(0); cl.setContentsMargins(0,0,0,0)

        self._corte_subtabs = QTabWidget()
        self._corte_subtabs.setStyleSheet(f"""
            QTabWidget::pane {{ border:none; background:{BG}; }}
            QTabBar::tab {{
                background:#ECF0F1; color:{MUTED};
                padding:7px 16px; font-size:12px; font-weight:600;
                border-radius:0; margin-right:2px;
            }}
            QTabBar::tab:selected {{ background:{BG}; color:{PRIMARY}; border-bottom:3px solid {PRIMARY}; }}
            QTabBar::tab:hover {{ color:{TEXT}; }}
        """)
        self._corte_subtabs.addTab(self._build_corte_diario(), "📊  Corte Diario")
        self._corte_subtabs.addTab(self._build_turnos_tab(),   "🔄  Turnos")
        self._corte_subtabs.addTab(self._build_bitacora_tab(), "📋  Bitácora")
        cl.addWidget(self._corte_subtabs)

        layout.addWidget(self._corte_content)
        return w

    def _build_corte_diario(self):
        """Subtab del corte diario — igual que antes."""
        w = QWidget(); w.setStyleSheet(f"background:{BG};")
        cl = QVBoxLayout(w); cl.setContentsMargins(12,12,12,12); cl.setSpacing(12)

        date_row = QHBoxLayout()
        date_lbl = QLabel("Fecha:"); date_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600;")
        date_row.addWidget(date_lbl)
        self._corte_fecha = QLineEdit(); self._corte_fecha.setText(date.today().strftime("%Y-%m-%d"))
        self._corte_fecha.setFixedWidth(140)
        self._corte_fecha.setStyleSheet(f"border:1.5px solid {BORDER}; border-radius:8px; padding:7px 12px; font-size:13px; background:white; color:{TEXT};")
        date_row.addWidget(self._corte_fecha)
        calc_btn = _btn("📊  Calcular", PRIMARY, SECONDARY)
        calc_btn.clicked.connect(self._corte_calcular)
        date_row.addWidget(calc_btn); date_row.addStretch()
        cl.addLayout(date_row)

        self._corte_cards = QWidget()
        self._corte_cards_layout = QGridLayout(self._corte_cards)
        self._corte_cards_layout.setSpacing(10)
        cl.addWidget(self._corte_cards)

        comp_lbl = QLabel("📈  Comparativo últimos 7 días")
        comp_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        comp_lbl.setStyleSheet(f"color:{PRIMARY};")
        cl.addWidget(comp_lbl)

        self._corte_comp_table = QTableWidget()
        self._corte_comp_table.setColumnCount(2)
        self._corte_comp_table.setHorizontalHeaderLabels(["Fecha", "Total del día"])
        self._corte_comp_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._corte_comp_table.verticalHeader().setVisible(False)
        self._corte_comp_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._corte_comp_table.setMaximumHeight(200)
        self._corte_comp_table.setAlternatingRowColors(True)
        self._corte_comp_table.setStyleSheet(f"""
            QTableWidget {{ background:{CARD}; border-radius:8px; border:1px solid {BORDER}; font-size:13px; }}
            QHeaderView::section {{ background:{PRIMARY}; color:white; padding:8px; font-weight:700; border:none; }}
            QTableWidget::item {{ padding:8px; color:{TEXT}; }}
            QTableWidget::item:alternate {{ background:#F8FBFC; }}
        """)
        cl.addWidget(self._corte_comp_table)

        notas_lbl = QLabel("Notas:"); notas_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600;")
        cl.addWidget(notas_lbl)
        self._corte_notas = QTextEdit()
        self._corte_notas.setPlaceholderText("Observaciones del día…")
        self._corte_notas.setMaximumHeight(60)
        self._corte_notas.setStyleSheet(f"border:1.5px solid {BORDER}; border-radius:8px; padding:7px; font-size:13px; background:white; color:{TEXT};")
        cl.addWidget(self._corte_notas)

        act_row = QHBoxLayout()
        guardar_btn = _btn("💾  Guardar Corte", SUCCESS, "#1E8449")
        guardar_btn.clicked.connect(self._corte_guardar)
        pdf_btn = _btn("📄  Exportar PDF", "#8E44AD", "#7D3C98")
        pdf_btn.clicked.connect(self._corte_pdf)
        act_row.addWidget(guardar_btn); act_row.addWidget(pdf_btn); act_row.addStretch()
        cl.addLayout(act_row)
        return w

    def _build_turnos_tab(self):
        """Subtab de gestión de turnos."""
        w = QWidget(); w.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(w); lay.setContentsMargins(12,12,12,12); lay.setSpacing(12)

        # Turno activo card
        self._turno_activo_frame = QFrame()
        self._turno_activo_frame.setStyleSheet(f"""
            QFrame {{
                background:#E8F5E9; border-radius:10px;
                border:2px solid {SUCCESS};
            }}
        """)
        tfl = QVBoxLayout(self._turno_activo_frame); tfl.setContentsMargins(16,12,16,12); tfl.setSpacing(6)

        top_row = QHBoxLayout()
        self._turno_status_lbl = QLabel("⏱️  Sin turno activo")
        self._turno_status_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._turno_status_lbl.setStyleSheet(f"color:{SUCCESS}; background:transparent;")
        top_row.addWidget(self._turno_status_lbl)
        top_row.addStretch()

        self._iniciar_turno_btn = _btn("▶️  Iniciar Turno", SUCCESS, "#1E8449", h=36)
        self._iniciar_turno_btn.clicked.connect(self._iniciar_turno)
        top_row.addWidget(self._iniciar_turno_btn)

        self._cerrar_turno_btn = _btn("⏹️  Cerrar Turno", DANGER, "#C0392B", h=36)
        self._cerrar_turno_btn.setVisible(False)
        self._cerrar_turno_btn.clicked.connect(self._cerrar_turno)
        top_row.addWidget(self._cerrar_turno_btn)

        tfl.addLayout(top_row)

        self._turno_info_lbl = QLabel("")
        self._turno_info_lbl.setStyleSheet(f"color:{MUTED}; font-size:12px; background:transparent;")
        tfl.addWidget(self._turno_info_lbl)

        # Totales del turno actual
        self._turno_totales_lbl = QLabel("")
        self._turno_totales_lbl.setStyleSheet(f"color:{TEXT}; font-size:13px; font-weight:600; background:transparent;")
        tfl.addWidget(self._turno_totales_lbl)

        lay.addWidget(self._turno_activo_frame)

        # Historial de turnos
        hist_lbl = QLabel("Historial de Turnos")
        hist_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        hist_lbl.setStyleSheet(f"color:{PRIMARY};")
        lay.addWidget(hist_lbl)

        self._turnos_table = QTableWidget()
        self._turnos_table.setColumnCount(7)
        self._turnos_table.setHorizontalHeaderLabels(
            ["Turno", "Fecha", "Inicio", "Fin", "Cobros", "Cancelados", "Total"]
        )
        self._turnos_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._turnos_table.verticalHeader().setVisible(False)
        self._turnos_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._turnos_table.setAlternatingRowColors(True)
        self._turnos_table.setStyleSheet(f"""
            QTableWidget {{ background:{CARD}; border-radius:10px; border:1px solid {BORDER}; font-size:13px; }}
            QHeaderView::section {{ background:{PRIMARY}; color:white; padding:8px; font-weight:700; border:none; }}
            QTableWidget::item {{ padding:8px; color:{TEXT}; }}
            QTableWidget::item:alternate {{ background:#F8FBFC; }}
        """)
        lay.addWidget(self._turnos_table)
        return w

    def _build_bitacora_tab(self):
        """Subtab de bitácora de acciones."""
        w = QWidget(); w.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(w); lay.setContentsMargins(12,12,12,12); lay.setSpacing(10)

        top = QHBoxLayout()
        title = QLabel("📋  Registro de Acciones")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY};")
        top.addWidget(title); top.addStretch()
        refresh_btn = _btn("🔄", "#ECF0F1", "#D5DBDB", TEXT, w=42)
        refresh_btn.clicked.connect(self._load_bitacora)
        top.addWidget(refresh_btn)
        lay.addLayout(top)

        info = QLabel("Aquí se registran eliminaciones, cambios importantes y acciones del sistema.")
        info.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        lay.addWidget(info)

        self._bitacora_table = QTableWidget()
        self._bitacora_table.setColumnCount(4)
        self._bitacora_table.setHorizontalHeaderLabels(["Fecha", "Usuario", "Acción", "Detalle"])
        self._bitacora_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._bitacora_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._bitacora_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._bitacora_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._bitacora_table.verticalHeader().setVisible(False)
        self._bitacora_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._bitacora_table.setAlternatingRowColors(True)
        self._bitacora_table.setWordWrap(True)
        self._bitacora_table.setStyleSheet(f"""
            QTableWidget {{ background:{CARD}; border-radius:10px; border:1px solid {BORDER}; font-size:12px; }}
            QHeaderView::section {{ background:{PRIMARY}; color:white; padding:8px; font-weight:700; border:none; }}
            QTableWidget::item {{ padding:8px; color:{TEXT}; }}
            QTableWidget::item:alternate {{ background:#F8FBFC; }}
        """)
        lay.addWidget(self._bitacora_table)
        return w

    def _corte_login(self):
        from modules.corte import LoginCorteDialog
        dlg = LoginCorteDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._corte_usuario = dlg.usuario_logueado
            self._corte_user_lbl.setText(f"✅ {self._corte_usuario['nombre']} ({self._corte_usuario['rol']})")
            self._corte_locked.setVisible(False)
            self._corte_content.setVisible(True)
            self._login_btn.setVisible(False)
            self._logout_btn.setVisible(True)
            self._refresh_btn.setVisible(True)
            self._corte_calcular()
            self._load_turno_activo()
            self._load_bitacora()

    def _iniciar_turno(self):
        ta = turno_activo()
        if ta:
            m = QMessageBox(self); m.setWindowTitle("Aviso")
            m.setText("Ya hay un turno activo. Ciérralo antes de iniciar uno nuevo.")
            m.setStyleSheet("color:black; background:white;"); m.exec()
            return

        # Determinar número de turno del día
        from modules.corte import historial_turnos
        from datetime import date as _date
        turnos_hoy = [t for t in historial_turnos() if t["fecha"] == _date.today().strftime("%Y-%m-%d")]
        num = len(turnos_hoy) + 1

        turno_id = iniciar_turno(self._corte_usuario["id"], num)
        registrar_en_bitacora(
            self._corte_usuario["id"],
            "INICIAR_TURNO",
            f"Turno #{num} iniciado por {self._corte_usuario['nombre']}"
        )
        self._load_turno_activo()
        self._load_bitacora()

        m = QMessageBox(self); m.setWindowTitle("Turno iniciado")
        m.setText(f"✅ Turno #{num} iniciado correctamente.")
        m.setStyleSheet("color:black; background:white;"); m.exec()

    def _cerrar_turno(self):
        ta = turno_activo()
        if not ta:
            return

        m = QMessageBox(self); m.setWindowTitle("Cerrar Turno")
        m.setText(f"¿Cerrar el Turno #{ta['numero_turno']}?\nSe guardarán todos los totales del turno.")
        m.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        m.setStyleSheet("color:black; background:white;")
        if m.exec() != QMessageBox.StandardButton.Yes:
            return

        datos = cerrar_turno(ta["id"])
        registrar_en_bitacora(
            self._corte_usuario["id"],
            "CERRAR_TURNO",
            f"Turno #{ta['numero_turno']} cerrado. Total: ${datos['total_general']:,.2f} | "
            f"Cobros: {datos['num_cobros']} | Cancelados: {datos['num_cancelados']}"
        )
        self._load_turno_activo()
        self._load_bitacora()
        self._load_historial_turnos()

        m2 = QMessageBox(self); m2.setWindowTitle("Turno cerrado")
        m2.setText(
            f"✅ Turno #{ta['numero_turno']} cerrado.\n\n"
            f"Total: ${datos['total_general']:,.2f}\n"
            f"Efectivo: ${datos['total_efectivo']:,.2f}\n"
            f"Tarjeta: ${datos['total_tarjeta']:,.2f}\n"
            f"Cobros: {datos['num_cobros']} | Cancelados: {datos['num_cancelados']}"
        )
        m2.setStyleSheet("color:black; background:white;"); m2.exec()

    def _load_turno_activo(self):
        ta = turno_activo()
        if ta:
            self._turno_status_lbl.setText(f"⏱️  Turno #{ta['numero_turno']} en curso")
            self._turno_info_lbl.setText(
                f"Iniciado a las {ta['hora_inicio']} por {ta.get('usuario_nombre','—')}"
            )
            # Calcular totales actuales
            datos = calcular_turno(ta["id"])
            self._turno_totales_lbl.setText(
                f"💰 Total: ${datos['total_general']:,.2f}  |  "
                f"Cobros: {datos['num_cobros']}  |  "
                f"Cancelados: {datos['num_cancelados']}"
            )
            self._turno_activo_frame.setStyleSheet(f"""
                QFrame {{ background:#E8F5E9; border-radius:10px; border:2px solid {SUCCESS}; }}
            """)
            self._iniciar_turno_btn.setVisible(False)
            self._cerrar_turno_btn.setVisible(True)
        else:
            self._turno_status_lbl.setText("⏸️  Sin turno activo")
            self._turno_info_lbl.setText("Inicia un turno para registrar cobros de este período")
            self._turno_totales_lbl.setText("")
            self._turno_activo_frame.setStyleSheet(f"""
                QFrame {{ background:#FFF8E1; border-radius:10px; border:2px solid {WARNING}; }}
            """)
            self._iniciar_turno_btn.setVisible(True)
            self._cerrar_turno_btn.setVisible(False)

        self._load_historial_turnos()

    def _load_historial_turnos(self):
        turnos = historial_turnos()
        self._turnos_table.setRowCount(len(turnos))
        for i, t in enumerate(turnos):
            estado_color = SUCCESS if t["estado"] == "cerrado" else WARNING
            vals = [
                f"Turno #{t['numero_turno']}",
                t["fecha"],
                t["hora_inicio"][:5],
                t.get("hora_fin","")[:5] if t.get("hora_fin") else "—",
                str(t.get("num_cobros", 0)),
                str(t.get("num_cancelados", 0)),
                f"${t.get('total_general', 0):,.2f}",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if col == 6:
                    item.setForeground(QBrush(QColor(estado_color)))
                    f = QFont(); f.setBold(True); item.setFont(f)
                self._turnos_table.setItem(i, col, item)
            self._turnos_table.setRowHeight(i, 40)

    def _load_bitacora(self):
        registros = obtener_bitacora_completa()
        self._bitacora_table.setRowCount(len(registros))
        colores_accion = {
            "ELIMINAR_COBRO": DANGER,
            "INICIAR_TURNO":  SUCCESS,
            "CERRAR_TURNO":   WARNING,
        }
        for i, r in enumerate(registros):
            fecha = r.get("fecha","")[:16].replace("T"," ")
            accion = r.get("accion","—")
            color = colores_accion.get(accion, TEXT)
            vals = [
                fecha,
                r.get("usuario_nombre","Sistema") or "Sistema",
                accion,
                r.get("detalle","—") or "—",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if col == 2:
                    item.setForeground(QBrush(QColor(color)))
                    f = QFont(); f.setBold(True); item.setFont(f)
                self._bitacora_table.setItem(i, col, item)
            self._bitacora_table.setRowHeight(i, 40)

    def _corte_logout(self):
        self._corte_usuario = None
        self._corte_datos   = None
        self._corte_user_lbl.setText("🔒 Sin sesión")
        self._corte_locked.setVisible(True)
        self._corte_content.setVisible(False)
        self._login_btn.setVisible(True)
        self._logout_btn.setVisible(False)
        self._refresh_btn.setVisible(False)

    def _corte_calcular(self):
        fecha = self._corte_fecha.text().strip()
        try:
            datetime.strptime(fecha, "%Y-%m-%d")
        except ValueError:
            return
        self._corte_datos = calcular_corte(fecha)
        d = self._corte_datos

        # Clear cards
        while self._corte_cards_layout.count():
            item = self._corte_cards_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        cards = [
            ("💵","Efectivo",          f"${d['total_efectivo']:,.2f}",           SUCCESS),
            ("💳","Tarjeta",           f"${d['total_tarjeta']:,.2f}",            SECONDARY),
            ("🏦","Transferencia",     f"${d['total_transferencia']:,.2f}",      WARNING),
            ("📋","Crédito",           f"${d['total_credito']:,.2f}",            "#8E44AD"),
            ("🏆","TOTAL GENERAL",     f"${d['total_general']:,.2f}",            PRIMARY),
            ("👥","Pacientes",         str(d["num_pacientes"]),                   ACCENT),
            ("✅","Citas Completadas", str(d["citas_completadas"]),               SUCCESS),
            ("🗑️","Cobros Eliminados", str(d.get("cobros_eliminados", 0)),       DANGER),
        ]
        for i, (icon, label, value, color) in enumerate(cards):
            card = QFrame()
            card.setStyleSheet(f"background:white; border-radius:10px; border:1.5px solid {BORDER};")
            card.setFixedHeight(90)
            cl2 = QVBoxLayout(card); cl2.setContentsMargins(12,10,12,10); cl2.setSpacing(2)
            ic = QLabel(icon); ic.setFont(QFont("Segoe UI",18)); ic.setStyleSheet("border:none; background:transparent;")
            vl = QLabel(value); vl.setFont(QFont("Segoe UI",15,QFont.Weight.Bold)); vl.setStyleSheet(f"color:{color}; border:none; background:transparent;")
            lb = QLabel(label); lb.setStyleSheet(f"color:{MUTED}; font-size:10px; border:none; background:transparent;")
            cl2.addWidget(ic); cl2.addWidget(vl); cl2.addWidget(lb)
            self._corte_cards_layout.addWidget(card, i//4, i%4)

        # Comparativo
        comp = d["comparativo"]
        self._corte_comp_table.setRowCount(len(comp))
        for row, item in enumerate(comp):
            dt = datetime.strptime(item["fecha"], "%Y-%m-%d")
            dia = _DIAS[dt.weekday()].capitalize()
            fecha_str = f"{dia} {dt.day}/{dt.month}/{dt.year}"
            if item["fecha"] == fecha:
                fecha_str += "  ← hoy"
            fi = QTableWidgetItem(fecha_str)
            ti = QTableWidgetItem(f"${item['total']:,.2f}")
            ti.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if item["fecha"] == fecha:
                for itm in [fi, ti]:
                    itm.setForeground(QBrush(QColor(PRIMARY)))
                    font = QFont(); font.setBold(True); itm.setFont(font)
            self._corte_comp_table.setItem(row, 0, fi)
            self._corte_comp_table.setItem(row, 1, ti)
            self._corte_comp_table.setRowHeight(row, 34)

    def _corte_guardar(self):
        if not self._corte_datos or not self._corte_usuario:
            return
        guardar_corte(self._corte_datos, self._corte_usuario["id"], self._corte_notas.toPlainText())
        m = QMessageBox(self); m.setWindowTitle("Guardado")
        m.setText("✅ Corte guardado correctamente.")
        m.setStyleSheet("color:black; background:white;"); m.exec()

    def _corte_pdf(self):
        if not self._corte_datos or not self._corte_usuario:
            m = QMessageBox(self); m.setWindowTitle("Aviso")
            m.setText("Primero calcula el corte del día.")
            m.setStyleSheet("color:black; background:white;"); m.exec()
            return
        fecha_str = self._corte_datos["fecha"].replace("-","")
        path, _ = QFileDialog.getSaveFileName(self, "Guardar PDF", f"corte_{fecha_str}.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            exportar_pdf(self._corte_datos, self._corte_usuario["nombre"],
                         self._corte_notas.toPlainText(), path)
            m = QMessageBox(self); m.setWindowTitle("PDF Exportado")
            m.setText(f"✅ PDF guardado en:\n{path}")
            m.setStyleSheet("color:black; background:white;"); m.exec()
        except Exception as e:
            m = QMessageBox(self); m.setWindowTitle("Error")
            m.setText(f"No se pudo exportar:\n{str(e)}")
            m.setStyleSheet("color:black; background:white;"); m.exec()

    # ── Actions ───────────────────────────────────────────────────────────────
    def _nuevo_cobro(self):
        dlg = NuevoPagoDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            crear_pago(dlg.result_data)
            self._load_cobros()
            self._load_pendientes()
            m = QMessageBox(self); m.setWindowTitle("Éxito")
            m.setText("✅ Cobro registrado correctamente.")
            m.setStyleSheet("color:black; background:white;"); m.exec()

    def _ver_detalle(self, pago_id):
        p = obtener_pago_por_id(pago_id)
        if p:
            DetallePagoDialog(p, self).exec()

    def _eliminar_pago(self, pago_id):
        p = obtener_pago_por_id(pago_id)
        if not p:
            return

        # Pedir autenticación admin
        auth = AdminAuthDialog(self, "eliminar este cobro")
        if auth.exec() != QDialog.DialogCode.Accepted:
            return

        nombre   = p.get("paciente_nombre", "—")
        concepto = p.get("concepto", "—")
        monto    = p.get("monto_total", 0)

        m = QMessageBox(self); m.setWindowTitle("Confirmar eliminación")
        m.setText(
            f"¿Eliminar el cobro de <b>{nombre}</b>?<br>"
            f"Concepto: {concepto} — ${monto:,.2f}<br><br>"
            f"<b>Esta acción quedará registrada en la bitácora.</b>"
        )
        m.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        m.setStyleSheet("color:black; background:white;")
        if m.exec() == QMessageBox.StandardButton.Yes:
            detalle = (f"Cobro ID#{pago_id} | Paciente: {nombre} | "
                       f"Concepto: {concepto} | Monto: ${monto:,.2f}")
            eliminar_pago(pago_id, auth.usuario_autenticado["id"], detalle)
            self._load_cobros()
            self._load_pendientes()
            # Refrescar turno y bitácora si están visibles
            try:
                self._load_turno_activo()
                self._load_bitacora()
            except Exception:
                pass
            m2 = QMessageBox(self); m2.setWindowTitle("Eliminado")
            m2.setText("✅ Cobro eliminado y registrado en bitácora.")
            m2.setStyleSheet("color:black; background:white;"); m2.exec()

    def _registrar_abono(self, pago_id):
        p = obtener_pago_por_id(pago_id)
        if not p:
            return
        dlg = AbonoDialog(p, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            r = dlg.result
            ok = registrar_abono(pago_id, r["monto"], r["metodo"], r["notas"])
            if ok:
                self._load_cobros()
                self._load_pendientes()
                m = QMessageBox(self); m.setWindowTitle("Éxito")
                m.setText(f"✅ Abono de ${r['monto']:,.2f} registrado.")
                m.setStyleSheet("color:black; background:white;"); m.exec()
            else:
                m = QMessageBox(self); m.setWindowTitle("Error")
                m.setText("No se pudo registrar el abono.")
                m.setStyleSheet("color:black; background:white;"); m.exec()

    def _ver_plan(self, pago):
        dlg = DetallePlanWidget(pago, self)
        dlg.exec()
        self._load_pendientes()

    def _make_table(self, headers):
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        t.horizontalHeader().setMinimumSectionSize(80)
        t.horizontalHeader().setStretchLastSection(False)
        t.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        t.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        t.setAlternatingRowColors(True)
        t.setShowGrid(False)
        t.setStyleSheet(f"""
            QTableWidget {{
                background:{CARD}; border-radius:10px;
                border:1px solid {BORDER}; font-size:13px;
            }}
            QHeaderView::section {{
                background:{PRIMARY}; color:white;
                padding:10px; font-weight:700; border:none;
            }}
            QTableWidget::item {{ padding:8px; color:{TEXT}; }}
            QTableWidget::item:selected {{ background:#D6EAF8; color:{TEXT}; }}
            QTableWidget::item:alternate {{ background:#F8FBFC; }}
        """)
        return t
