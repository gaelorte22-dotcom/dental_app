"""
plan_pagos.py
Calculadora de planes de pago con calendario de cuotas,
frecuencias (semanal, quincenal, fechas manuales) e interés configurable.
"""

import os, sys
from datetime import datetime, date, timedelta

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialog, QMessageBox, QFrame, QScrollArea,
    QFormLayout, QComboBox, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QDoubleSpinBox, QSpinBox,
    QGridLayout, QTabWidget, QDateEdit, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QBrush, QColor

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database.db_manager import get_connection

# ── Palette ───────────────────────────────────────────────────────────────────
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

METODOS   = ["Efectivo", "Tarjeta", "Transferencia", "Crédito"]
_MESES    = ["","enero","febrero","marzo","abril","mayo","junio",
             "julio","agosto","septiembre","octubre","noviembre","diciembre"]
_DIAS     = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]


def _btn(label, color, hover, text_color="white", w=None):
    b = QPushButton(label)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if w: b.setFixedWidth(w)
    b.setStyleSheet(f"""
        QPushButton {{
            background:{color}; color:{text_color};
            border:none; border-radius:8px;
            padding:8px 18px; font-size:13px; font-weight:600;
        }}
        QPushButton:hover {{ background:{hover}; }}
    """)
    return b


def _field_style():
    return f"""
        QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QDateEdit {{
            border:1.5px solid {BORDER}; border-radius:8px;
            padding:7px 10px; font-size:13px;
            background:white; color:{TEXT};
        }}
        QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus,
        QComboBox:focus, QDateEdit:focus {{ border-color:{SECONDARY}; }}
        QComboBox QAbstractItemView {{ color:{TEXT}; background:white; }}
    """


# ── DB helpers ────────────────────────────────────────────────────────────────
def crear_plan(pago_id, datos: dict, cuotas: list) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO plan_pagos
            (pago_id, monto_total, interes_pct, monto_con_interes,
             num_cuotas, monto_cuota, frecuencia, fecha_inicio, notas)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (
        pago_id,
        datos["monto_total"], datos["interes_pct"], datos["monto_con_interes"],
        datos["num_cuotas"], datos["monto_cuota"],
        datos["frecuencia"], datos["fecha_inicio"], datos.get("notas","")
    ))
    plan_id = cur.lastrowid

    for c in cuotas:
        cur.execute("""
            INSERT INTO cuotas (plan_id, numero, fecha_vencimiento, monto)
            VALUES (?,?,?,?)
        """, (plan_id, c["numero"], c["fecha"], c["monto"]))

    conn.commit()
    conn.close()
    return plan_id


def obtener_planes(pago_id: int) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM plan_pagos WHERE pago_id=? ORDER BY id DESC", (pago_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def obtener_cuotas(plan_id: int) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM cuotas WHERE plan_id=? ORDER BY numero", (plan_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def pagar_cuota(cuota_id: int, metodo: str, notas: str = ""):
    conn = get_connection()
    conn.execute("""
        UPDATE cuotas SET estado='pagada', fecha_pago=?, metodo_pago=?, notas=?
        WHERE id=?
    """, (date.today().strftime("%Y-%m-%d"), metodo, notas, cuota_id))

    # Revisar si todas las cuotas del plan están pagadas
    cur = conn.cursor()
    cur.execute("SELECT plan_id FROM cuotas WHERE id=?", (cuota_id,))
    plan_id = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM cuotas WHERE plan_id=? AND estado='pendiente'", (plan_id,))
    pendientes = cur.fetchone()[0]
    if pendientes == 0:
        conn.execute("UPDATE plan_pagos SET estado='completado' WHERE id=?", (plan_id,))
        # Marcar pago padre como pagado
        cur.execute("SELECT pago_id FROM plan_pagos WHERE id=?", (plan_id,))
        pago_id = cur.fetchone()[0]
        conn.execute("UPDATE pagos SET estado='pagado' WHERE id=?", (pago_id,))

    # Actualizar monto_pagado del pago padre
    cur.execute("SELECT pago_id, monto_cuota FROM plan_pagos WHERE id=?", (plan_id,))
    row = cur.fetchone()
    if row:
        cur.execute("""
            SELECT COUNT(*) FROM cuotas
            WHERE plan_id=? AND estado='pagada'
        """, (plan_id,))
        pagadas = cur.fetchone()[0]
        nuevo_pagado = pagadas * row["monto_cuota"]
        cur.execute("SELECT monto_total FROM pagos WHERE id=?", (row["pago_id"],))
        monto_total = cur.fetchone()[0]
        nuevo_estado = "pagado" if nuevo_pagado >= monto_total else "parcial"
        conn.execute("""
            UPDATE pagos SET monto_pagado=?, estado=? WHERE id=?
        """, (min(nuevo_pagado, monto_total), nuevo_estado, row["pago_id"]))

    conn.commit()
    conn.close()


def obtener_cuotas_proximas(dias=7) -> list:
    """Cuotas que vencen en los próximos N días."""
    conn = get_connection()
    cur = conn.cursor()
    hoy = date.today().strftime("%Y-%m-%d")
    limite = (date.today() + timedelta(days=dias)).strftime("%Y-%m-%d")
    cur.execute("""
        SELECT c.*, pp.frecuencia, pp.pago_id,
               pa.nombre || ' ' || pa.apellido AS paciente_nombre,
               p.concepto
        FROM cuotas c
        JOIN plan_pagos pp ON c.plan_id = pp.id
        JOIN pagos p ON pp.pago_id = p.id
        JOIN pacientes pa ON p.paciente_id = pa.id
        WHERE c.estado='pendiente'
          AND c.fecha_vencimiento BETWEEN ? AND ?
        ORDER BY c.fecha_vencimiento
    """, (hoy, limite))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ── Calculadora de fechas ─────────────────────────────────────────────────────
def generar_fechas(fecha_inicio: str, num_cuotas: int,
                   frecuencia: str, intervalo_dias: int = 7,
                   fechas_manuales: list = None) -> list:
    inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
    fechas = []

    if frecuencia == "manual" and fechas_manuales:
        return fechas_manuales[:num_cuotas]

    for i in range(num_cuotas):
        if frecuencia == "semanal":
            # intervalo_dias = número de días entre pagos (7, 14, 21…)
            d = inicio + timedelta(days=intervalo_dias * i)
        elif frecuencia == "quincenal":
            d = inicio + timedelta(days=15 * i)
        else:
            d = inicio + timedelta(days=intervalo_dias * i)
        fechas.append(d.strftime("%Y-%m-%d"))

    return fechas


# ── Calculadora Dialog ────────────────────────────────────────────────────────
class CalculadoraPlanDialog(QDialog):
    def __init__(self, pago: dict, parent=None):
        super().__init__(parent)
        self.pago = pago
        self.setWindowTitle(f"Plan de Pagos — {pago.get('paciente_nombre','')}")
        self.setMinimumWidth(640)
        self.setMinimumHeight(600)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self._fechas_manuales = []
        self._cuotas_preview  = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(0)

        # Header
        hdr = QWidget(); hdr.setFixedHeight(80)
        hdr.setStyleSheet(f"background:{PRIMARY};")
        hl = QVBoxLayout(hdr); hl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel("📅  Calculadora de Plan de Pagos")
        t.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        t.setStyleSheet("color:white;"); t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(t)
        s = QLabel(f"{self.pago.get('paciente_nombre','')}  —  {self.pago.get('concepto','')}")
        s.setStyleSheet("color:#B2EBF2; font-size:11px;")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(s)
        layout.addWidget(hdr)

        body = QScrollArea(); body.setWidgetResizable(True)
        body.setStyleSheet("border:none; background:transparent;")
        inner = QWidget(); inner.setStyleSheet(f"background:{BG};")
        il = QVBoxLayout(inner); il.setContentsMargins(28,20,28,20); il.setSpacing(14)
        body.setWidget(inner)

        fs = _field_style()

        # ── Sección 1: Parámetros ─────────────────────────────────────────────
        sec1 = self._section("⚙️  Parámetros del Plan")
        il.addWidget(sec1)

        params = QFrame()
        params.setStyleSheet(f"background:{CARD}; border-radius:10px; border:1px solid {BORDER};")
        pl = QGridLayout(params); pl.setContentsMargins(18,14,18,14); pl.setSpacing(12)

        def lbl(t):
            l = QLabel(t); l.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:12px; border:none; background:transparent;")
            return l

        # Monto total (readonly, viene del pago)
        self.monto_lbl = QLabel(f"${self.pago['monto_total']:,.2f}")
        self.monto_lbl.setStyleSheet(f"color:{PRIMARY}; font-size:16px; font-weight:700; border:none; background:transparent;")

        # Interés
        self.interes = QDoubleSpinBox()
        self.interes.setRange(0, 100); self.interes.setSuffix(" %")
        self.interes.setDecimals(2); self.interes.setSingleStep(0.5)
        self.interes.setStyleSheet(fs)
        self.interes.valueChanged.connect(self._recalcular)

        # Número de cuotas
        self.num_cuotas = QSpinBox()
        self.num_cuotas.setRange(2, 60); self.num_cuotas.setValue(4)
        self.num_cuotas.setStyleSheet(fs)
        self.num_cuotas.valueChanged.connect(self._recalcular)

        # Frecuencia
        self.frecuencia = QComboBox()
        self.frecuencia.addItems(["Semanal", "Quincenal", "Fechas manuales"])
        self.frecuencia.setStyleSheet(fs)
        self.frecuencia.currentIndexChanged.connect(self._on_frecuencia)

        # Intervalo semanal
        self.intervalo_lbl = QLabel("Cada cuántos días:")
        self.intervalo_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:12px; border:none; background:transparent;")
        self.intervalo = QSpinBox()
        self.intervalo.setRange(1, 90); self.intervalo.setValue(7)
        self.intervalo.setSuffix(" días")
        self.intervalo.setSpecialValueText("")
        self.intervalo.setStyleSheet(fs)
        self.intervalo.valueChanged.connect(self._recalcular)

        # Fecha inicio
        self.fecha_inicio = QDateEdit()
        self.fecha_inicio.setDate(QDate.currentDate())
        self.fecha_inicio.setCalendarPopup(True)
        self.fecha_inicio.setStyleSheet(fs)
        self.fecha_inicio.dateChanged.connect(self._recalcular)

        pl.addWidget(lbl("Monto total:"),     0, 0); pl.addWidget(self.monto_lbl,    0, 1)
        pl.addWidget(lbl("Interés (%):"),     0, 2); pl.addWidget(self.interes,      0, 3)
        pl.addWidget(lbl("Número de cuotas:"),1, 0); pl.addWidget(self.num_cuotas,   1, 1)
        pl.addWidget(lbl("Frecuencia:"),      1, 2); pl.addWidget(self.frecuencia,   1, 3)
        pl.addWidget(self.intervalo_lbl,      2, 0); pl.addWidget(self.intervalo,    2, 1)
        pl.addWidget(lbl("Fecha 1er pago:"),  2, 2); pl.addWidget(self.fecha_inicio, 2, 3)
        il.addWidget(params)

        # Botón agregar fecha manual
        self.manual_frame = QFrame()
        self.manual_frame.setStyleSheet(f"background:{CARD}; border-radius:10px; border:1px solid {BORDER};")
        mfl = QVBoxLayout(self.manual_frame); mfl.setContentsMargins(18,12,18,12); mfl.setSpacing(8)
        mf_top = QHBoxLayout()
        mf_lbl = QLabel("📅  Fechas manuales de pago:")
        mf_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:12px; border:none; background:transparent;")
        mf_top.addWidget(mf_lbl); mf_top.addStretch()
        add_fecha_btn = _btn("＋ Agregar fecha", SECONDARY, PRIMARY, w=140)
        add_fecha_btn.clicked.connect(self._agregar_fecha_manual)
        mf_top.addWidget(add_fecha_btn)
        mfl.addLayout(mf_top)

        self.manual_fechas_layout = QHBoxLayout()
        self.manual_fechas_layout.setSpacing(8)
        self.manual_fechas_layout.addStretch()
        mfl.addLayout(self.manual_fechas_layout)
        self.manual_frame.setVisible(False)
        il.addWidget(self.manual_frame)

        # ── Sección 2: Resumen ────────────────────────────────────────────────
        il.addWidget(self._section("💡  Resumen del Plan"))

        self.resumen_frame = QFrame()
        self.resumen_frame.setStyleSheet(f"background:{CARD}; border-radius:10px; border:1px solid {BORDER};")
        rl = QGridLayout(self.resumen_frame); rl.setContentsMargins(18,14,18,14); rl.setSpacing(10)

        self.r_total_interes = QLabel("$0.00")
        self.r_monto_final   = QLabel("$0.00")
        self.r_cuota         = QLabel("$0.00")
        self.r_num           = QLabel("0")

        for w in [self.r_total_interes, self.r_monto_final, self.r_cuota, self.r_num]:
            w.setStyleSheet(f"color:{PRIMARY}; font-size:15px; font-weight:700; border:none; background:transparent;")

        rl.addWidget(lbl("Total con interés:"), 0, 0); rl.addWidget(self.r_monto_final,   0, 1)
        rl.addWidget(lbl("Interés total:"),     0, 2); rl.addWidget(self.r_total_interes, 0, 3)
        rl.addWidget(lbl("Monto por cuota:"),   1, 0); rl.addWidget(self.r_cuota,         1, 1)
        rl.addWidget(lbl("Número de cuotas:"),  1, 2); rl.addWidget(self.r_num,           1, 3)
        il.addWidget(self.resumen_frame)

        # ── Sección 3: Calendario preview ────────────────────────────────────
        il.addWidget(self._section("📋  Calendario de Pagos"))

        self.calendario_table = QTableWidget()
        self.calendario_table.setColumnCount(3)
        self.calendario_table.setHorizontalHeaderLabels(["#", "Fecha de Vencimiento", "Monto"])
        self.calendario_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.calendario_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.calendario_table.verticalHeader().setVisible(False)
        self.calendario_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.calendario_table.setMaximumHeight(220)
        self.calendario_table.setAlternatingRowColors(True)
        self.calendario_table.setStyleSheet(f"""
            QTableWidget {{ background:{CARD}; border-radius:8px; border:1px solid {BORDER}; font-size:13px; }}
            QHeaderView::section {{ background:{PRIMARY}; color:white; padding:8px; font-weight:700; border:none; }}
            QTableWidget::item {{ padding:8px; color:{TEXT}; }}
            QTableWidget::item:alternate {{ background:#F8FBFC; }}
        """)
        il.addWidget(self.calendario_table)

        # Notas
        notas_lbl = QLabel("Notas del plan:")
        notas_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
        il.addWidget(notas_lbl)
        self.notas = QTextEdit()
        self.notas.setPlaceholderText("Acuerdos con el paciente, condiciones especiales…")
        self.notas.setMaximumHeight(60)
        self.notas.setStyleSheet(f"border:1.5px solid {BORDER}; border-radius:8px; padding:8px; font-size:13px; background:white; color:{TEXT};")
        il.addWidget(self.notas)

        # Botones
        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = _btn("Cancelar", "#ECF0F1", "#D5DBDB", TEXT)
        cancel.clicked.connect(self.reject)
        crear_btn = _btn("✅  Crear Plan de Pagos", PRIMARY, SECONDARY)
        crear_btn.clicked.connect(self._crear)
        btn_row.addWidget(cancel); btn_row.addWidget(crear_btn)
        il.addLayout(btn_row)

        layout.addWidget(body)
        self._recalcular()

    def _section(self, title):
        lbl = QLabel(title)
        lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color:{PRIMARY}; background:transparent;")
        return lbl

    def _on_frecuencia(self, idx):
        es_manual = idx == 2
        self.manual_frame.setVisible(es_manual)
        self.intervalo_lbl.setVisible(idx == 0)
        self.intervalo.setVisible(idx == 0)
        self._recalcular()

    def _agregar_fecha_manual(self):
        de = QDateEdit()
        de.setDate(QDate.currentDate())
        de.setCalendarPopup(True)
        de.setStyleSheet(_field_style())
        de.setFixedWidth(130)

        wrapper = QFrame()
        wrapper.setStyleSheet(f"background:{BG}; border-radius:6px; border:1px solid {BORDER};")
        wl = QHBoxLayout(wrapper); wl.setContentsMargins(6,4,6,4); wl.setSpacing(4)
        num_lbl = QLabel(f"#{len(self._fechas_manuales)+1}")
        num_lbl.setStyleSheet(f"color:{MUTED}; font-size:11px; border:none; background:transparent;")
        del_btn = QPushButton("✕")
        del_btn.setFixedSize(20, 20)
        del_btn.setStyleSheet(f"background:{DANGER}; color:white; border-radius:4px; border:none; font-size:10px;")
        del_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        wl.addWidget(num_lbl); wl.addWidget(de); wl.addWidget(del_btn)

        idx = len(self._fechas_manuales)
        self._fechas_manuales.append(de)

        # Remove stretch, add widget, re-add stretch
        self.manual_fechas_layout.removeItem(
            self.manual_fechas_layout.itemAt(self.manual_fechas_layout.count()-1)
        )
        self.manual_fechas_layout.addWidget(wrapper)
        self.manual_fechas_layout.addStretch()

        de.dateChanged.connect(self._recalcular)
        del_btn.clicked.connect(lambda _, w=wrapper, d=de: self._quitar_fecha(w, d))
        self._recalcular()

    def _quitar_fecha(self, wrapper, de):
        self._fechas_manuales = [d for d in self._fechas_manuales if d is not de]
        wrapper.deleteLater()
        self._recalcular()

    def _recalcular(self):
        monto       = self.pago["monto_total"]
        interes_pct = self.interes.value()
        num         = self.num_cuotas.value()
        interes_monto = monto * interes_pct / 100
        total_final   = monto + interes_monto
        cuota         = total_final / num if num > 0 else 0

        self.r_monto_final.setText(f"${total_final:,.2f}")
        self.r_total_interes.setText(f"${interes_monto:,.2f}")
        self.r_cuota.setText(f"${cuota:,.2f}")
        self.r_num.setText(str(num))

        # Generar fechas
        freq_idx = self.frecuencia.currentIndex()
        fecha_inicio = self.fecha_inicio.date().toString("yyyy-MM-dd")

        if freq_idx == 0:   # Semanal
            frecuencia = "semanal"
            intervalo  = self.intervalo.value()  # ya son días (7, 14, 21…)
            fechas = generar_fechas(fecha_inicio, num, frecuencia, intervalo)
        elif freq_idx == 1: # Quincenal
            frecuencia = "quincenal"
            fechas = generar_fechas(fecha_inicio, num, frecuencia)
        else:               # Manual
            frecuencia = "manual"
            fechas = [d.date().toString("yyyy-MM-dd") for d in self._fechas_manuales]
            fechas = fechas[:num]

        # Preview tabla
        self._cuotas_preview = []
        self.calendario_table.setRowCount(min(num, len(fechas)) if fechas else num)

        for i in range(self.calendario_table.rowCount()):
            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.calendario_table.setItem(i, 0, num_item)

            if i < len(fechas):
                fecha_str = fechas[i]
                try:
                    dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                    dia = _DIAS[dt.weekday()].capitalize()
                    fecha_display = f"{dia}, {dt.day} de {_MESES[dt.month]} {dt.year}"
                except Exception:
                    fecha_display = fecha_str
            else:
                fecha_str = "—"
                fecha_display = "— (agregar fecha)"

            fecha_item = QTableWidgetItem(fecha_display)
            monto_item = QTableWidgetItem(f"${cuota:,.2f}")
            monto_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            # Marcar vencidas en rojo
            try:
                if fecha_str != "—" and datetime.strptime(fecha_str, "%Y-%m-%d").date() < date.today():
                    for itm in [fecha_item, monto_item]:
                        itm.setForeground(QBrush(QColor(DANGER)))
            except Exception:
                pass

            self.calendario_table.setItem(i, 1, fecha_item)
            self.calendario_table.setItem(i, 2, monto_item)
            self.calendario_table.setRowHeight(i, 36)

            if fecha_str != "—":
                self._cuotas_preview.append({"numero": i+1, "fecha": fecha_str, "monto": cuota})

    def _crear(self):
        num = self.num_cuotas.value()
        if len(self._cuotas_preview) < num and self.frecuencia.currentIndex() == 2:
            self._msg(f"Faltan fechas manuales. Tienes {len(self._cuotas_preview)} de {num}.")
            return
        if not self._cuotas_preview:
            self._msg("No hay cuotas generadas. Revisa los parámetros.")
            return

        monto       = self.pago["monto_total"]
        interes_pct = self.interes.value()
        interes_monto = monto * interes_pct / 100
        total_final   = monto + interes_monto
        cuota_monto   = total_final / num

        freq_map = {0: "semanal", 1: "quincenal", 2: "manual"}
        freq = freq_map[self.frecuencia.currentIndex()]

        self.result = {
            "datos": {
                "monto_total":       monto,
                "interes_pct":       interes_pct,
                "monto_con_interes": total_final,
                "num_cuotas":        num,
                "monto_cuota":       cuota_monto,
                "frecuencia":        freq,
                "fecha_inicio":      self._cuotas_preview[0]["fecha"],
                "notas":             self.notas.toPlainText(),
            },
            "cuotas": self._cuotas_preview,
        }
        self.accept()

    def _msg(self, txt):
        m = QMessageBox(self); m.setWindowTitle("Aviso")
        m.setText(txt); m.setStyleSheet("color:black; background:white;")
        m.exec()


# ── Pagar cuota dialog ────────────────────────────────────────────────────────
class PagarCuotaDialog(QDialog):
    def __init__(self, cuota: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Pagar Cuota #{cuota['numero']}")
        self.setFixedWidth(380)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self._build(cuota)

    def _build(self, c):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        title = QLabel(f"💳  Cuota #{c['numero']}")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY};")
        layout.addWidget(title)

        info = QFrame()
        info.setStyleSheet(f"background:{CARD}; border-radius:8px; border:1px solid {BORDER};")
        il = QVBoxLayout(info); il.setContentsMargins(14,10,14,10); il.setSpacing(4)
        for k, v in [("Vencimiento:", c["fecha_vencimiento"]), ("Monto:", f"${c['monto']:,.2f}")]:
            row = QHBoxLayout()
            lk = QLabel(k); lk.setStyleSheet(f"color:{MUTED}; font-size:12px; border:none; background:transparent;")
            lv = QLabel(v); lv.setStyleSheet(f"color:{TEXT}; font-size:12px; font-weight:700; border:none; background:transparent;")
            row.addWidget(lk); row.addWidget(lv); row.addStretch()
            il.addLayout(row)
        layout.addWidget(info)

        fs = _field_style()
        self.metodo = QComboBox(); self.metodo.addItems(METODOS); self.metodo.setStyleSheet(fs)
        self.notas  = QLineEdit(); self.notas.setPlaceholderText("Observaciones…"); self.notas.setStyleSheet(fs)

        form = QFormLayout(); form.setSpacing(10)
        def lbl(t):
            l = QLabel(t); l.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
            return l
        form.addRow(lbl("Método *"), self.metodo)
        form.addRow(lbl("Notas"),    self.notas)
        layout.addLayout(form)

        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = _btn("Cancelar", "#ECF0F1", "#D5DBDB", TEXT)
        cancel.clicked.connect(self.reject)
        pagar = _btn("✅  Registrar Pago", SUCCESS, "#1E8449")
        pagar.clicked.connect(self.accept)
        btn_row.addWidget(cancel); btn_row.addWidget(pagar)
        layout.addLayout(btn_row)


# ── Detalle plan widget (usado dentro de facturacion) ─────────────────────────
class DetallePlanWidget(QDialog):
    def __init__(self, pago: dict, parent=None):
        super().__init__(parent)
        self.pago = pago
        self.setWindowTitle(f"Plan de Pagos — {pago.get('paciente_nombre','')}")
        self.setMinimumSize(680, 540)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel(f"📅  Plan de Pagos — {self.pago.get('concepto','')}")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY};")
        layout.addWidget(title)

        planes = obtener_planes(self.pago["id"])
        if not planes:
            empty = QLabel("No hay planes de pago registrados para este cobro.")
            empty.setStyleSheet(f"color:{MUTED}; font-size:13px;")
            layout.addWidget(empty)
            nuevo_btn = _btn("＋  Crear Plan de Pagos", PRIMARY, SECONDARY)
            nuevo_btn.clicked.connect(self._nuevo_plan)
            layout.addWidget(nuevo_btn)
            self._tabla_cuotas = None
            self._plan_actual  = None
            return

        # Selector de plan si hay varios
        plan_row = QHBoxLayout()
        plan_lbl = QLabel("Plan activo:")
        plan_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
        plan_row.addWidget(plan_lbl)

        self.plan_selector = QComboBox()
        self.plan_selector.setStyleSheet(f"""
            QComboBox {{ border:1.5px solid {BORDER}; border-radius:8px;
                padding:7px 10px; font-size:13px; background:white; color:{TEXT}; }}
            QComboBox QAbstractItemView {{ color:{TEXT}; background:white; }}
        """)
        for p in planes:
            label = f"Plan #{p['id']} — {p['num_cuotas']} cuotas — {p['estado'].capitalize()}"
            self.plan_selector.addItem(label, p["id"])
        self.plan_selector.currentIndexChanged.connect(self._load_plan)
        plan_row.addWidget(self.plan_selector); plan_row.addStretch()

        nuevo_btn = _btn("＋  Nuevo Plan", SECONDARY, PRIMARY)
        nuevo_btn.clicked.connect(self._nuevo_plan)
        plan_row.addWidget(nuevo_btn)
        layout.addLayout(plan_row)

        # Resumen del plan
        self.resumen_lbl = QLabel()
        self.resumen_lbl.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        layout.addWidget(self.resumen_lbl)

        # Tabla cuotas
        cuotas_lbl = QLabel("Cuotas:")
        cuotas_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        cuotas_lbl.setStyleSheet(f"color:{TEXT};")
        layout.addWidget(cuotas_lbl)

        self._tabla_cuotas = QTableWidget()
        self._tabla_cuotas.setColumnCount(5)
        self._tabla_cuotas.setHorizontalHeaderLabels(["#", "Vencimiento", "Monto", "Estado", "Acción"])
        self._tabla_cuotas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tabla_cuotas.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._tabla_cuotas.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._tabla_cuotas.verticalHeader().setVisible(False)
        self._tabla_cuotas.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla_cuotas.setAlternatingRowColors(True)
        self._tabla_cuotas.setStyleSheet(f"""
            QTableWidget {{ background:{CARD}; border-radius:10px; border:1px solid {BORDER}; font-size:13px; }}
            QHeaderView::section {{ background:{PRIMARY}; color:white; padding:8px; font-weight:700; border:none; }}
            QTableWidget::item {{ padding:8px; color:{TEXT}; }}
            QTableWidget::item:alternate {{ background:#F8FBFC; }}
        """)
        layout.addWidget(self._tabla_cuotas)

        close = _btn("Cerrar", "#ECF0F1", "#D5DBDB", TEXT)
        close.clicked.connect(self.accept)
        layout.addWidget(close)

        self._planes = planes
        self._load_plan(0)

    def _load_plan(self, idx):
        if not hasattr(self, '_planes') or not self._planes:
            return
        plan_id = self.plan_selector.itemData(idx)
        plan = next((p for p in self._planes if p["id"] == plan_id), self._planes[0])
        self._plan_actual = plan

        interes = plan["interes_pct"]
        self.resumen_lbl.setText(
            f"Total: ${plan['monto_con_interes']:,.2f}  |  "
            f"Interés: {interes}%  |  "
            f"Cuota: ${plan['monto_cuota']:,.2f}  |  "
            f"Frecuencia: {plan['frecuencia'].capitalize()}  |  "
            f"Estado: {plan['estado'].capitalize()}"
        )
        self._load_cuotas(plan_id)

    def _load_cuotas(self, plan_id):
        cuotas = obtener_cuotas(plan_id)
        self._tabla_cuotas.setRowCount(len(cuotas))

        for row, c in enumerate(cuotas):
            try:
                dt = datetime.strptime(c["fecha_vencimiento"], "%Y-%m-%d")
                dia = _DIAS[dt.weekday()].capitalize()
                fecha_display = f"{dia} {dt.day}/{dt.month}/{dt.year}"
            except Exception:
                fecha_display = c["fecha_vencimiento"]

            estado = c["estado"]
            estado_color = SUCCESS if estado == "pagada" else (
                DANGER if datetime.strptime(c["fecha_vencimiento"], "%Y-%m-%d").date() < date.today()
                and estado == "pendiente" else WARNING
            )

            num_item    = QTableWidgetItem(str(c["numero"]))
            num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            fecha_item  = QTableWidgetItem(fecha_display)
            monto_item  = QTableWidgetItem(f"${c['monto']:,.2f}")
            monto_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            estado_item = QTableWidgetItem(
                f"✅ Pagada ({c['fecha_pago'][:10]})" if estado == "pagada" else "⏳ Pendiente"
            )
            estado_item.setForeground(QBrush(QColor(estado_color)))
            font = QFont(); font.setBold(True); estado_item.setFont(font)

            self._tabla_cuotas.setItem(row, 0, num_item)
            self._tabla_cuotas.setItem(row, 1, fecha_item)
            self._tabla_cuotas.setItem(row, 2, monto_item)
            self._tabla_cuotas.setItem(row, 3, estado_item)

            if estado == "pendiente":
                cell = QWidget(); cell.setStyleSheet("background:transparent;")
                hb = QHBoxLayout(cell); hb.setContentsMargins(4,2,4,2)
                pagar_btn = _btn("💳 Pagar", SUCCESS, "#1E8449")
                pagar_btn.setFixedHeight(28)
                pagar_btn.clicked.connect(lambda _, cid=c["id"], cn=c: self._pagar(cid, cn))
                hb.addWidget(pagar_btn)
                self._tabla_cuotas.setCellWidget(row, 4, cell)
            else:
                self._tabla_cuotas.setItem(row, 4, QTableWidgetItem(""))

            self._tabla_cuotas.setRowHeight(row, 42)

    def _pagar(self, cuota_id, cuota):
        dlg = PagarCuotaDialog(cuota, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            pagar_cuota(cuota_id, dlg.metodo.currentText(), dlg.notas.text())
            self._load_cuotas(self._plan_actual["id"])
            m = QMessageBox(self); m.setWindowTitle("Éxito")
            m.setText(f"✅ Cuota #{cuota['numero']} registrada como pagada.")
            m.setStyleSheet("color:black; background:white;"); m.exec()

    def _nuevo_plan(self):
        dlg = CalculadoraPlanDialog(self.pago, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            crear_plan(self.pago["id"], dlg.result["datos"], dlg.result["cuotas"])
            m = QMessageBox(self); m.setWindowTitle("Plan creado")
            m.setText("✅ Plan de pagos creado correctamente.")
            m.setStyleSheet("color:black; background:white;"); m.exec()
            self.accept()  # Cerrar y reabrir para refrescar
