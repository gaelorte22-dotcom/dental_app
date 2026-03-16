"""
expedientes.py
Módulo de Historial Clínico / Expedientes:
  - Búsqueda y selección de paciente
  - Historial de tratamientos
  - Odontograma interactivo (32 dientes)
  - Alergias y notas médicas
  - Recetas / indicaciones
  - Archivos adjuntos (radiografías, fotos)
  - Exportar expediente a PDF
"""

import os, sys, shutil
from datetime import datetime, date

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QDialog, QMessageBox, QFrame, QTabWidget,
    QFormLayout, QComboBox, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QDoubleSpinBox, QScrollArea,
    QGridLayout, QFileDialog, QSizePolicy, QListWidget,
    QListWidgetItem, QSplitter, QApplication
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QFont, QBrush, QColor, QPixmap, QPainter, QPen

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database.db_manager import get_connection, obtener_pacientes, obtener_paciente_por_id

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

_MESES = ["","enero","febrero","marzo","abril","mayo","junio",
          "julio","agosto","septiembre","octubre","noviembre","diciembre"]

ESTADOS_DIENTE = {
    "sano":       ("#27AE60", "Sano"),
    "caries":     ("#E74C3C", "Caries"),
    "obturado":   ("#3498DB", "Obturado"),
    "corona":     ("#9B59B6", "Corona"),
    "extraccion": ("#7F8C8D", "Extraído"),
    "implante":   ("#F39C12", "Implante"),
    "fractura":   ("#E67E22", "Fractura"),
}

def _get_app_data_dir():
    if os.name == 'nt':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.path.expanduser('~')
    app_dir = os.path.join(base, 'DentalApp')
    os.makedirs(app_dir, exist_ok=True)
    return app_dir

ARCHIVOS_DIR = os.path.join(_get_app_data_dir(), "archivos_pacientes")
os.makedirs(ARCHIVOS_DIR, exist_ok=True)


def _btn(label, color, hover, text_color="white", w=None, h=None):
    b = QPushButton(label)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if w: b.setFixedWidth(w)
    if h: b.setFixedHeight(h)
    b.setStyleSheet(f"""
        QPushButton {{
            background:{color}; color:{text_color};
            border:none; border-radius:8px;
            padding:8px 16px; font-size:13px; font-weight:600;
        }}
        QPushButton:hover {{ background:{hover}; }}
    """)
    return b


def _fs():
    return f"""
        QLineEdit, QDoubleSpinBox, QComboBox, QTextEdit {{
            border:1.5px solid {BORDER}; border-radius:8px;
            padding:7px 10px; font-size:13px; background:white; color:{TEXT};
        }}
        QLineEdit:focus, QDoubleSpinBox:focus,
        QComboBox:focus, QTextEdit:focus {{ border-color:{SECONDARY}; }}
        QComboBox QAbstractItemView {{ color:{TEXT}; background:white; }}
    """


# ── DB helpers ────────────────────────────────────────────────────────────────
def get_historial(paciente_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM historial_clinico WHERE paciente_id=? ORDER BY fecha DESC", (paciente_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def crear_tratamiento(datos):
    conn = get_connection()
    conn.execute("""
        INSERT INTO historial_clinico
            (paciente_id, fecha, tratamiento, diente, descripcion, costo, dentista, estado)
        VALUES (:paciente_id,:fecha,:tratamiento,:diente,:descripcion,:costo,:dentista,:estado)
    """, datos)
    conn.commit()
    conn.close()


def eliminar_tratamiento(tid):
    conn = get_connection()
    conn.execute("DELETE FROM historial_clinico WHERE id=?", (tid,))
    conn.commit()
    conn.close()


def get_odontograma(paciente_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM odontograma WHERE paciente_id=?", (paciente_id,))
    rows = {r["diente_num"]: dict(r) for r in cur.fetchall()}
    conn.close()
    return rows


def set_diente(paciente_id, diente_num, estado, notas=""):
    color = ESTADOS_DIENTE.get(estado, ("gray",""))[0]
    conn = get_connection()
    conn.execute("""
        INSERT INTO odontograma (paciente_id, diente_num, estado, color, notas, fecha_actualizacion)
        VALUES (?,?,?,?,?,?)
        ON CONFLICT(paciente_id, diente_num)
        DO UPDATE SET estado=excluded.estado, color=excluded.color,
                      notas=excluded.notas, fecha_actualizacion=excluded.fecha_actualizacion
    """, (paciente_id, diente_num, estado, color,
          notas, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()


def get_recetas(paciente_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM recetas WHERE paciente_id=? ORDER BY fecha DESC", (paciente_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def crear_receta(datos):
    conn = get_connection()
    conn.execute("""
        INSERT INTO recetas (paciente_id, fecha, medicamentos, indicaciones, dentista)
        VALUES (:paciente_id,:fecha,:medicamentos,:indicaciones,:dentista)
    """, datos)
    conn.commit()
    conn.close()


def eliminar_receta(rid):
    conn = get_connection()
    conn.execute("DELETE FROM recetas WHERE id=?", (rid,))
    conn.commit()
    conn.close()


def get_archivos(paciente_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM archivos WHERE paciente_id=? ORDER BY fecha DESC", (paciente_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def guardar_archivo(paciente_id, ruta_origen, descripcion):
    nombre = os.path.basename(ruta_origen)
    ext = os.path.splitext(nombre)[1].lower()
    tipo = "imagen" if ext in [".jpg",".jpeg",".png",".gif",".bmp"] else "documento"
    dest_dir = os.path.join(ARCHIVOS_DIR, str(paciente_id))
    os.makedirs(dest_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
    dest = os.path.join(dest_dir, timestamp + nombre)
    shutil.copy2(ruta_origen, dest)
    conn = get_connection()
    conn.execute("""
        INSERT INTO archivos (paciente_id, nombre, ruta, tipo, descripcion)
        VALUES (?,?,?,?,?)
    """, (paciente_id, nombre, dest, tipo, descripcion))
    conn.commit()
    conn.close()


def eliminar_archivo(aid, ruta):
    try:
        if os.path.exists(ruta):
            os.remove(ruta)
    except Exception:
        pass
    conn = get_connection()
    conn.execute("DELETE FROM archivos WHERE id=?", (aid,))
    conn.commit()
    conn.close()


# ── Tooth button ──────────────────────────────────────────────────────────────
class ToothButton(QPushButton):
    def __init__(self, numero, label, parent=None):
        super().__init__(parent)
        self.numero = numero
        self.label  = label
        self.estado = "sano"
        self.setFixedSize(38, 48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(f"Diente {numero}")
        self._refresh()

    def set_estado(self, estado):
        self.estado = estado
        self._refresh()

    def _refresh(self):
        color = ESTADOS_DIENTE.get(self.estado, ("#27AE60",""))[0]
        self.setStyleSheet(f"""
            QPushButton {{
                background:{color}; color:white;
                border:2px solid white; border-radius:6px;
                font-size:9px; font-weight:700;
            }}
            QPushButton:hover {{ border:2px solid {PRIMARY}; }}
        """)
        self.setText(self.label)


# ── Odontograma widget ────────────────────────────────────────────────────────
class OdontogramaWidget(QWidget):
    changed = pyqtSignal(int, str)  # diente_num, estado

    # Superior derecho → izquierdo (18..11), superior izq (21..28)
    # Inferior derecho → izquierdo (48..41), inferior izq (31..38)
    SUPERIOR = list(range(18, 10, -1)) + list(range(21, 29))
    INFERIOR = list(range(48, 40, -1)) + list(range(31, 39))

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{CARD};")
        self._buttons = {}
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Leyenda
        legend = QHBoxLayout()
        legend.addStretch()
        for estado, (color, nombre) in ESTADOS_DIENTE.items():
            dot = QLabel(f"● {nombre}")
            dot.setStyleSheet(f"color:{color}; font-size:11px; font-weight:600;")
            legend.addWidget(dot)
        legend.addStretch()
        layout.addLayout(legend)

        # Superior
        sup_lbl = QLabel("Superior")
        sup_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sup_lbl.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        layout.addWidget(sup_lbl)

        sup_row = QHBoxLayout()
        sup_row.setSpacing(3)
        sup_row.addStretch()
        for n in self.SUPERIOR:
            btn = ToothButton(n, str(n))
            btn.clicked.connect(lambda _, num=n: self._on_click(num))
            self._buttons[n] = btn
            sup_row.addWidget(btn)
        sup_row.addStretch()
        layout.addLayout(sup_row)

        # Separador
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{BORDER};"); sep.setFixedHeight(1)
        layout.addWidget(sep)

        # Inferior
        inf_row = QHBoxLayout()
        inf_row.setSpacing(3)
        inf_row.addStretch()
        for n in self.INFERIOR:
            btn = ToothButton(n, str(n))
            btn.clicked.connect(lambda _, num=n: self._on_click(num))
            self._buttons[n] = btn
            inf_row.addWidget(btn)
        inf_row.addStretch()
        layout.addLayout(inf_row)

        inf_lbl = QLabel("Inferior")
        inf_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inf_lbl.setStyleSheet(f"color:{MUTED}; font-size:11px;")
        layout.addWidget(inf_lbl)

    def load(self, datos: dict):
        for num, btn in self._buttons.items():
            if num in datos:
                btn.set_estado(datos[num]["estado"])
                btn.setToolTip(f"Diente {num}: {datos[num]['estado'].capitalize()}\n{datos[num].get('notas','')}")
            else:
                btn.set_estado("sano")
                btn.setToolTip(f"Diente {num}")

    def _on_click(self, num):
        dlg = DienteDialog(num, self._buttons[num].estado, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._buttons[num].set_estado(dlg.estado)
            self._buttons[num].setToolTip(f"Diente {num}: {dlg.estado.capitalize()}\n{dlg.notas}")
            self.changed.emit(num, dlg.estado)
            self._last_notas = dlg.notas
            self._last_num   = num

    def get_last_notas(self):
        return getattr(self, "_last_notas", "")


# ── Diente dialog ─────────────────────────────────────────────────────────────
class DienteDialog(QDialog):
    def __init__(self, numero, estado_actual, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Diente {numero}")
        self.setFixedWidth(340)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self.estado = estado_actual
        self.notas  = ""
        self._build(numero, estado_actual)

    def _build(self, numero, estado_actual):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel(f"🦷  Diente {numero}")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY};")
        layout.addWidget(title)

        estado_lbl = QLabel("Estado:")
        estado_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600;")
        layout.addWidget(estado_lbl)

        self.estado_combo = QComboBox()
        self.estado_combo.setStyleSheet(_fs())
        for key, (color, nombre) in ESTADOS_DIENTE.items():
            self.estado_combo.addItem(nombre, key)
            if key == estado_actual:
                self.estado_combo.setCurrentIndex(self.estado_combo.count()-1)
        layout.addWidget(self.estado_combo)

        notas_lbl = QLabel("Notas:")
        notas_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600;")
        layout.addWidget(notas_lbl)

        self.notas_input = QTextEdit()
        self.notas_input.setMaximumHeight(70)
        self.notas_input.setStyleSheet(_fs())
        layout.addWidget(self.notas_input)

        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = _btn("Cancelar", "#ECF0F1", "#D5DBDB", TEXT)
        cancel.clicked.connect(self.reject)
        ok = _btn("✅  Guardar", PRIMARY, SECONDARY)
        ok.clicked.connect(self._save)
        btn_row.addWidget(cancel); btn_row.addWidget(ok)
        layout.addLayout(btn_row)

    def _save(self):
        self.estado = self.estado_combo.currentData()
        self.notas  = self.notas_input.toPlainText().strip()
        self.accept()


# ── Tratamiento Dialog ────────────────────────────────────────────────────────
class TratamientoDialog(QDialog):
    def __init__(self, parent=None, datos=None):
        super().__init__(parent)
        self.setWindowTitle("Tratamiento")
        self.setMinimumWidth(480)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self._build(datos)

    def _build(self, d):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(12)

        title = QLabel("🦷  Registrar Tratamiento")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY};")
        layout.addWidget(title)

        fs = _fs()

        self.tratamiento = QLineEdit()
        self.tratamiento.setPlaceholderText("Ej. Extracción, Limpieza, Obturación…")
        self.tratamiento.setStyleSheet(fs)
        if d: self.tratamiento.setText(d.get("tratamiento",""))

        self.diente = QLineEdit()
        self.diente.setPlaceholderText("Ej. 16, 21-23, Superior…")
        self.diente.setStyleSheet(fs)
        if d: self.diente.setText(d.get("diente",""))

        self.descripcion = QTextEdit()
        self.descripcion.setPlaceholderText("Descripción del procedimiento…")
        self.descripcion.setMaximumHeight(80)
        self.descripcion.setStyleSheet(fs)
        if d: self.descripcion.setText(d.get("descripcion",""))

        self.costo = QDoubleSpinBox()
        self.costo.setRange(0, 999999); self.costo.setPrefix("$ ")
        self.costo.setDecimals(2); self.costo.setSingleStep(50)
        self.costo.setStyleSheet(fs)
        if d: self.costo.setValue(d.get("costo",0))

        self.dentista = QLineEdit()
        self.dentista.setPlaceholderText("Nombre del dentista")
        self.dentista.setStyleSheet(fs)
        if d: self.dentista.setText(d.get("dentista",""))

        self.fecha = QLineEdit()
        self.fecha.setText(date.today().strftime("%Y-%m-%d"))
        self.fecha.setStyleSheet(fs)

        self.estado_combo = QComboBox()
        self.estado_combo.addItems(["realizado","pendiente","en_proceso"])
        self.estado_combo.setStyleSheet(fs)

        form = QFormLayout(); form.setSpacing(10)
        def lbl(t):
            l = QLabel(t); l.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
            return l
        form.addRow(lbl("Tratamiento *"), self.tratamiento)
        form.addRow(lbl("Diente(s)"),     self.diente)
        form.addRow(lbl("Descripción"),   self.descripcion)
        form.addRow(lbl("Costo"),         self.costo)
        form.addRow(lbl("Dentista"),      self.dentista)
        form.addRow(lbl("Fecha"),         self.fecha)
        form.addRow(lbl("Estado"),        self.estado_combo)
        layout.addLayout(form)

        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = _btn("Cancelar", "#ECF0F1", "#D5DBDB", TEXT)
        cancel.clicked.connect(self.reject)
        ok = _btn("💾  Guardar", PRIMARY, SECONDARY)
        ok.clicked.connect(self._save)
        btn_row.addWidget(cancel); btn_row.addWidget(ok)
        layout.addLayout(btn_row)

    def _save(self):
        if not self.tratamiento.text().strip():
            m = QMessageBox(self); m.setWindowTitle("Aviso")
            m.setText("El tratamiento es obligatorio.")
            m.setStyleSheet("color:black; background:white;"); m.exec()
            return
        self.result = {
            "tratamiento": self.tratamiento.text().strip(),
            "diente":      self.diente.text().strip(),
            "descripcion": self.descripcion.toPlainText().strip(),
            "costo":       self.costo.value(),
            "dentista":    self.dentista.text().strip(),
            "fecha":       self.fecha.text().strip(),
            "estado":      self.estado_combo.currentText(),
        }
        self.accept()


# ── Receta Dialog ─────────────────────────────────────────────────────────────
class RecetaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva Receta")
        self.setMinimumWidth(480)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(12)

        title = QLabel("📋  Nueva Receta / Indicaciones")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY};")
        layout.addWidget(title)

        fs = _fs()

        self.medicamentos = QTextEdit()
        self.medicamentos.setPlaceholderText(
            "Ej.\nAmoxicilina 500mg — 1 cápsula cada 8 hrs por 7 días\n"
            "Ibuprofeno 400mg — 1 tableta cada 6 hrs si hay dolor"
        )
        self.medicamentos.setMinimumHeight(100)
        self.medicamentos.setStyleSheet(fs)

        self.indicaciones = QTextEdit()
        self.indicaciones.setPlaceholderText(
            "Indicaciones postoperatorias, cuidados, dieta…"
        )
        self.indicaciones.setMinimumHeight(80)
        self.indicaciones.setStyleSheet(fs)

        self.dentista = QLineEdit()
        self.dentista.setPlaceholderText("Nombre del dentista")
        self.dentista.setStyleSheet(fs)

        form = QFormLayout(); form.setSpacing(10)
        def lbl(t):
            l = QLabel(t); l.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px;")
            return l
        form.addRow(lbl("Medicamentos *"), self.medicamentos)
        form.addRow(lbl("Indicaciones"),   self.indicaciones)
        form.addRow(lbl("Dentista"),       self.dentista)
        layout.addLayout(form)

        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = _btn("Cancelar", "#ECF0F1", "#D5DBDB", TEXT)
        cancel.clicked.connect(self.reject)
        ok = _btn("💾  Guardar", PRIMARY, SECONDARY)
        ok.clicked.connect(self._save)
        btn_row.addWidget(cancel); btn_row.addWidget(ok)
        layout.addLayout(btn_row)

    def _save(self):
        if not self.medicamentos.toPlainText().strip():
            m = QMessageBox(self); m.setWindowTitle("Aviso")
            m.setText("Los medicamentos son obligatorios.")
            m.setStyleSheet("color:black; background:white;"); m.exec()
            return
        self.result = {
            "medicamentos": self.medicamentos.toPlainText().strip(),
            "indicaciones": self.indicaciones.toPlainText().strip(),
            "dentista":     self.dentista.text().strip(),
            "fecha":        date.today().strftime("%Y-%m-%d"),
        }
        self.accept()


# ── PDF Export ────────────────────────────────────────────────────────────────
def exportar_pdf_expediente(paciente: dict, historial: list, odontograma: dict,
                             recetas: list, archivos: list, path: str):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     Table, TableStyle, HRFlowable)

    doc = SimpleDocTemplate(path, pagesize=letter,
                            leftMargin=0.8*inch, rightMargin=0.8*inch,
                            topMargin=0.8*inch, bottomMargin=0.8*inch)

    COLOR_PRIMARY = colors.HexColor(PRIMARY)
    COLOR_ACCENT  = colors.HexColor(ACCENT)
    COLOR_MUTED   = colors.HexColor(MUTED)
    COLOR_BG      = colors.HexColor("#F5F8FA")

    styles = getSampleStyleSheet()
    title_s   = ParagraphStyle("t",  fontSize=20, textColor=COLOR_PRIMARY,
                                fontName="Helvetica-Bold", spaceAfter=2)
    section_s = ParagraphStyle("s",  fontSize=13, textColor=COLOR_PRIMARY,
                                fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6)
    normal_s  = ParagraphStyle("n",  fontSize=10, textColor=colors.HexColor(TEXT),
                                fontName="Helvetica", spaceAfter=4)
    muted_s   = ParagraphStyle("m",  fontSize=9,  textColor=COLOR_MUTED,
                                fontName="Helvetica")

    story = []

    # Header
    story.append(Paragraph("🦷 DentalApp — Expediente Clínico", title_s))
    story.append(Paragraph(
        f"{paciente['nombre']} {paciente['apellido']}  —  "
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        muted_s
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=COLOR_PRIMARY, spaceAfter=10))

    # Datos del paciente
    story.append(Paragraph("Datos del Paciente", section_s))
    p_data = [["Campo", "Valor"]]
    for k, v in [
        ("Nombre completo", f"{paciente['nombre']} {paciente['apellido']}"),
        ("Fecha de nacimiento", paciente.get("fecha_nacimiento","—") or "—"),
        ("Género", paciente.get("genero","—") or "—"),
        ("Teléfono", paciente.get("telefono","—") or "—"),
        ("Email", paciente.get("email","—") or "—"),
        ("Alergias", paciente.get("alergias","—") or "—"),
        ("Notas médicas", paciente.get("notas","—") or "—"),
    ]:
        p_data.append([k, v or "—"])

    pt = Table(p_data, colWidths=[2*inch, 5.4*inch])
    pt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), COLOR_PRIMARY),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 10),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, COLOR_BG]),
        ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor(BORDER)),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    story.append(pt)

    # Historial
    if historial:
        story.append(Paragraph("Historial de Tratamientos", section_s))
        h_data = [["Fecha", "Tratamiento", "Diente", "Costo", "Dentista"]]
        for h in historial:
            h_data.append([
                h.get("fecha","")[:10],
                h.get("tratamiento","—"),
                h.get("diente","—") or "—",
                f"${h.get('costo',0):,.2f}",
                h.get("dentista","—") or "—",
            ])
        ht = Table(h_data, colWidths=[0.9*inch, 2.2*inch, 0.8*inch, 0.9*inch, 1.6*inch])
        ht.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), COLOR_ACCENT),
            ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, COLOR_BG]),
            ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor(BORDER)),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ]))
        story.append(ht)

    # Odontograma resumen
    dientes_afectados = {k: v for k, v in odontograma.items() if v["estado"] != "sano"}
    if dientes_afectados:
        story.append(Paragraph("Estado del Odontograma", section_s))
        o_data = [["Diente", "Estado", "Notas"]]
        for num, info in sorted(dientes_afectados.items()):
            nombre_estado = ESTADOS_DIENTE.get(info["estado"], ("","—"))[1]
            o_data.append([str(num), nombre_estado, info.get("notas","—") or "—"])
        ot = Table(o_data, colWidths=[1*inch, 2*inch, 4.4*inch])
        ot.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0), COLOR_PRIMARY),
            ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
            ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",      (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, COLOR_BG]),
            ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor(BORDER)),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ]))
        story.append(ot)

    # Recetas
    if recetas:
        story.append(Paragraph("Recetas e Indicaciones", section_s))
        for r in recetas:
            story.append(Paragraph(f"Fecha: {r.get('fecha','')[:10]}  |  Dentista: {r.get('dentista','—') or '—'}", muted_s))
            story.append(Paragraph(f"<b>Medicamentos:</b> {r.get('medicamentos','—')}", normal_s))
            if r.get("indicaciones"):
                story.append(Paragraph(f"<b>Indicaciones:</b> {r.get('indicaciones','')}", normal_s))
            story.append(Spacer(1, 6))

    # Footer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_MUTED))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"DentalApp v1.0.0  —  Expediente generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M hrs')}",
        ParagraphStyle("footer", fontSize=8, textColor=COLOR_MUTED,
                       fontName="Helvetica", alignment=1)
    ))

    doc.build(story)


# ── Expediente widget (per-patient) ──────────────────────────────────────────
class ExpedienteWidget(QWidget):
    def __init__(self, paciente: dict, parent=None):
        super().__init__(parent)
        self.paciente = paciente
        self.setStyleSheet(f"background:{BG};")
        self._build()
        self._load_all()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Patient header bar
        hdr = QWidget()
        hdr.setFixedHeight(64)
        hdr.setStyleSheet(f"background:{PRIMARY};")
        hl = QHBoxLayout(hdr); hl.setContentsMargins(20,0,20,0)
        name_lbl = QLabel(f"🦷  {self.paciente['nombre']} {self.paciente['apellido']}")
        name_lbl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        name_lbl.setStyleSheet("color:white;")
        hl.addWidget(name_lbl)
        hl.addStretch()

        pdf_btn = _btn("📄  Exportar PDF", "#8E44AD", "#7D3C98", h=36)
        pdf_btn.clicked.connect(self._exportar_pdf)
        hl.addWidget(pdf_btn)

        back_btn = _btn("← Volver", "#FFFFFF", "#ECF0F1", PRIMARY, h=36)
        back_btn.clicked.connect(self._volver)
        hl.addWidget(back_btn)
        root.addWidget(hdr)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border:none; background:{BG}; }}
            QTabBar::tab {{
                background:#ECF0F1; color:{MUTED};
                padding:9px 20px; font-size:13px; font-weight:600;
                border-radius:0; margin-right:2px;
            }}
            QTabBar::tab:selected {{ background:{BG}; color:{PRIMARY}; border-bottom:3px solid {PRIMARY}; }}
            QTabBar::tab:hover {{ color:{TEXT}; background:white; }}
        """)
        self.tabs.addTab(self._build_historial_tab(),  "📋  Historial")
        self.tabs.addTab(self._build_odontograma_tab(),"🦷  Odontograma")
        self.tabs.addTab(self._build_alergias_tab(),   "⚕️  Datos Médicos")
        self.tabs.addTab(self._build_recetas_tab(),    "📝  Recetas")
        self.tabs.addTab(self._build_archivos_tab(),   "📎  Archivos")
        root.addWidget(self.tabs)

    # ── TAB: Historial ────────────────────────────────────────────────────────
    def _build_historial_tab(self):
        w = QWidget(); w.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(w); lay.setContentsMargins(16,14,16,14); lay.setSpacing(10)

        top = QHBoxLayout()
        self.hist_search = QLineEdit()
        self.hist_search.setPlaceholderText("🔍  Buscar tratamiento…")
        self.hist_search.setStyleSheet(f"""
            QLineEdit {{
                border:1.5px solid {BORDER}; border-radius:20px;
                padding:7px 14px; font-size:13px; background:white; color:{TEXT};
            }}
        """)
        self.hist_search.textChanged.connect(self._load_historial)
        top.addWidget(self.hist_search)
        top.addStretch()
        nuevo_btn = _btn("＋  Agregar Tratamiento", PRIMARY, SECONDARY)
        nuevo_btn.clicked.connect(self._nuevo_tratamiento)
        top.addWidget(nuevo_btn)
        lay.addLayout(top)

        self.hist_stats = QLabel()
        self.hist_stats.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        lay.addWidget(self.hist_stats)

        self.hist_table = self._make_table(
            ["Fecha", "Tratamiento", "Diente", "Descripción", "Costo", "Dentista", "Estado", ""]
        )
        lay.addWidget(self.hist_table)
        return w

    def _load_historial(self):
        busqueda = self.hist_search.text().strip().lower()
        rows = get_historial(self.paciente["id"])
        if busqueda:
            rows = [r for r in rows if busqueda in (r.get("tratamiento","") or "").lower()
                    or busqueda in (r.get("descripcion","") or "").lower()]

        total = sum(r.get("costo",0) for r in rows)
        self.hist_stats.setText(f"{len(rows)} tratamiento(s)  |  Total: ${total:,.2f}")

        self.hist_table.setRowCount(len(rows))
        estado_colors = {"realizado": SUCCESS, "pendiente": WARNING, "en_proceso": SECONDARY}
        for i, r in enumerate(rows):
            vals = [
                r.get("fecha","")[:10],
                r.get("tratamiento","—"),
                r.get("diente","—") or "—",
                (r.get("descripcion","") or "")[:50],
                f"${r.get('costo',0):,.2f}",
                r.get("dentista","—") or "—",
                r.get("estado","realizado"),
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(val)
                if col == 6:
                    item.setForeground(QBrush(QColor(estado_colors.get(val, SUCCESS))))
                    f = QFont(); f.setBold(True); item.setFont(f)
                self.hist_table.setItem(i, col, item)

            cell = QWidget(); cell.setStyleSheet("background:transparent;")
            hb = QHBoxLayout(cell); hb.setContentsMargins(4,2,4,2)
            del_btn = _btn("🗑", DANGER, "#C0392B")
            del_btn.setFixedSize(34, 28)
            del_btn.clicked.connect(lambda _, rid=r["id"]: self._eliminar_tratamiento(rid))
            hb.addWidget(del_btn)
            self.hist_table.setCellWidget(i, 7, cell)
            self.hist_table.setRowHeight(i, 40)

    def _nuevo_tratamiento(self):
        dlg = TratamientoDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = {**dlg.result, "paciente_id": self.paciente["id"]}
            crear_tratamiento(data)
            self._load_historial()

    def _eliminar_tratamiento(self, tid):
        m = QMessageBox(self); m.setWindowTitle("Confirmar")
        m.setText("¿Eliminar este tratamiento del historial?")
        m.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        m.setStyleSheet("color:black; background:white;")
        if m.exec() == QMessageBox.StandardButton.Yes:
            eliminar_tratamiento(tid)
            self._load_historial()

    # ── TAB: Odontograma ──────────────────────────────────────────────────────
    def _build_odontograma_tab(self):
        w = QWidget(); w.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(w); lay.setContentsMargins(16,14,16,14); lay.setSpacing(10)

        info = QLabel("Haz clic en cualquier diente para cambiar su estado")
        info.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        lay.addWidget(info)

        self.odontograma = OdontogramaWidget()
        self.odontograma.changed.connect(self._on_diente_changed)
        lay.addWidget(self.odontograma)
        lay.addStretch()
        return w

    def _on_diente_changed(self, num, estado):
        notas = self.odontograma.get_last_notas()
        set_diente(self.paciente["id"], num, estado, notas)

    # ── TAB: Datos Médicos ────────────────────────────────────────────────────
    def _build_alergias_tab(self):
        w = QWidget(); w.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(w); lay.setContentsMargins(24,20,24,20); lay.setSpacing(14)

        title = QLabel("⚕️  Datos Médicos del Paciente")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY};")
        lay.addWidget(title)

        card = QFrame()
        card.setStyleSheet(f"background:{CARD}; border-radius:12px; border:1px solid {BORDER};")
        cl = QVBoxLayout(card); cl.setContentsMargins(20,16,20,16); cl.setSpacing(14)

        fs = _fs()

        def sec(t):
            l = QLabel(t); l.setFont(QFont("Segoe UI",12,QFont.Weight.Bold))
            l.setStyleSheet(f"color:{PRIMARY}; border:none; background:transparent;")
            return l

        def lbl(t):
            l = QLabel(t); l.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:13px; border:none; background:transparent;")
            return l

        cl.addWidget(sec("Alergias"))
        self.alergias_input = QTextEdit()
        self.alergias_input.setMaximumHeight(80)
        self.alergias_input.setStyleSheet(fs)
        self.alergias_input.setPlaceholderText("Penicilina, látex, anestesia…")
        cl.addWidget(self.alergias_input)

        cl.addWidget(sec("Condiciones Médicas"))
        self.condiciones_input = QTextEdit()
        self.condiciones_input.setMaximumHeight(80)
        self.condiciones_input.setStyleSheet(fs)
        self.condiciones_input.setPlaceholderText("Diabetes, hipertensión, embarazo…")
        cl.addWidget(self.condiciones_input)

        cl.addWidget(sec("Medicamentos Actuales"))
        self.medicamentos_input = QTextEdit()
        self.medicamentos_input.setMaximumHeight(80)
        self.medicamentos_input.setStyleSheet(fs)
        self.medicamentos_input.setPlaceholderText("Medicamentos que toma actualmente…")
        cl.addWidget(self.medicamentos_input)

        cl.addWidget(sec("Notas Adicionales"))
        self.notas_medicas_input = QTextEdit()
        self.notas_medicas_input.setMaximumHeight(80)
        self.notas_medicas_input.setStyleSheet(fs)
        self.notas_medicas_input.setPlaceholderText("Observaciones generales…")
        cl.addWidget(self.notas_medicas_input)

        guardar_btn = _btn("💾  Guardar Cambios", PRIMARY, SECONDARY, w=200)
        guardar_btn.clicked.connect(self._guardar_datos_medicos)
        cl.addWidget(guardar_btn)
        lay.addWidget(card)
        lay.addStretch()
        return w

    def _load_datos_medicos(self):
        p = obtener_paciente_por_id(self.paciente["id"])
        if p:
            self.alergias_input.setText(p.get("alergias","") or "")
            self.notas_medicas_input.setText(p.get("notas","") or "")

    def _guardar_datos_medicos(self):
        conn = get_connection()
        conn.execute("""
            UPDATE pacientes SET alergias=?, notas=? WHERE id=?
        """, (
            self.alergias_input.toPlainText().strip(),
            self.notas_medicas_input.toPlainText().strip(),
            self.paciente["id"]
        ))
        conn.commit()
        conn.close()
        m = QMessageBox(self); m.setWindowTitle("Guardado")
        m.setText("✅ Datos médicos actualizados.")
        m.setStyleSheet("color:black; background:white;"); m.exec()

    # ── TAB: Recetas ──────────────────────────────────────────────────────────
    def _build_recetas_tab(self):
        w = QWidget(); w.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(w); lay.setContentsMargins(16,14,16,14); lay.setSpacing(10)

        top = QHBoxLayout()
        top.addStretch()
        nueva_btn = _btn("＋  Nueva Receta", PRIMARY, SECONDARY)
        nueva_btn.clicked.connect(self._nueva_receta)
        top.addWidget(nueva_btn)
        lay.addLayout(top)

        self.recetas_table = self._make_table(["Fecha", "Medicamentos", "Indicaciones", "Dentista", ""])
        lay.addWidget(self.recetas_table)
        return w

    def _load_recetas(self):
        rows = get_recetas(self.paciente["id"])
        self.recetas_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            meds = (r.get("medicamentos","") or "")[:60]
            inds = (r.get("indicaciones","") or "")[:50]
            for col, val in enumerate([r.get("fecha","")[:10], meds, inds, r.get("dentista","—") or "—"]):
                self.recetas_table.setItem(i, col, QTableWidgetItem(val))

            cell = QWidget(); cell.setStyleSheet("background:transparent;")
            hb = QHBoxLayout(cell); hb.setContentsMargins(4,2,4,2)
            del_btn = _btn("🗑", DANGER, "#C0392B")
            del_btn.setFixedSize(34, 28)
            del_btn.clicked.connect(lambda _, rid=r["id"]: self._eliminar_receta(rid))
            hb.addWidget(del_btn)
            self.recetas_table.setCellWidget(i, 4, cell)
            self.recetas_table.setRowHeight(i, 40)

    def _nueva_receta(self):
        dlg = RecetaDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = {**dlg.result, "paciente_id": self.paciente["id"]}
            crear_receta(data)
            self._load_recetas()

    def _eliminar_receta(self, rid):
        m = QMessageBox(self); m.setWindowTitle("Confirmar")
        m.setText("¿Eliminar esta receta?")
        m.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        m.setStyleSheet("color:black; background:white;")
        if m.exec() == QMessageBox.StandardButton.Yes:
            eliminar_receta(rid); self._load_recetas()

    # ── TAB: Archivos ─────────────────────────────────────────────────────────
    def _build_archivos_tab(self):
        w = QWidget(); w.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(w); lay.setContentsMargins(16,14,16,14); lay.setSpacing(10)

        top = QHBoxLayout()
        info = QLabel("📎  Radiografías, fotos y documentos del paciente")
        info.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        top.addWidget(info); top.addStretch()
        subir_btn = _btn("＋  Subir Archivo", PRIMARY, SECONDARY)
        subir_btn.clicked.connect(self._subir_archivo)
        top.addWidget(subir_btn)
        lay.addLayout(top)

        self.archivos_table = self._make_table(["Fecha", "Nombre", "Tipo", "Descripción", ""])
        lay.addWidget(self.archivos_table)
        return w

    def _load_archivos(self):
        rows = get_archivos(self.paciente["id"])
        self.archivos_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for col, val in enumerate([
                r.get("fecha","")[:10],
                r.get("nombre","—"),
                r.get("tipo","—"),
                r.get("descripcion","—") or "—",
            ]):
                self.archivos_table.setItem(i, col, QTableWidgetItem(val))

            cell = QWidget(); cell.setStyleSheet("background:transparent;")
            hb = QHBoxLayout(cell); hb.setContentsMargins(4,2,4,2); hb.setSpacing(4)

            abrir_btn = _btn("📂", SECONDARY, PRIMARY)
            abrir_btn.setFixedSize(34, 28)
            abrir_btn.setToolTip("Abrir archivo")
            abrir_btn.clicked.connect(lambda _, ruta=r["ruta"]: self._abrir_archivo(ruta))

            del_btn = _btn("🗑", DANGER, "#C0392B")
            del_btn.setFixedSize(34, 28)
            del_btn.clicked.connect(lambda _, aid=r["id"], ruta=r["ruta"]: self._eliminar_archivo(aid, ruta))

            hb.addWidget(abrir_btn); hb.addWidget(del_btn)
            self.archivos_table.setCellWidget(i, 4, cell)
            self.archivos_table.setRowHeight(i, 40)

    def _subir_archivo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo", "",
            "Imágenes y documentos (*.jpg *.jpeg *.png *.pdf *.bmp *.gif);;Todos (*.*)"
        )
        if not path:
            return
        desc, ok = "", True
        dlg = QDialog(self); dlg.setWindowTitle("Descripción"); dlg.setFixedWidth(340)
        dlg.setStyleSheet(f"background:{BG}; color:{TEXT};")
        vl = QVBoxLayout(dlg); vl.setContentsMargins(20,16,20,16); vl.setSpacing(10)
        vl.addWidget(QLabel(f"Archivo: {os.path.basename(path)}"))
        inp = QLineEdit(); inp.setPlaceholderText("Descripción del archivo…")
        inp.setStyleSheet(_fs()); vl.addWidget(inp)
        br = QHBoxLayout(); br.addStretch()
        ok_btn = _btn("✅  Guardar", PRIMARY, SECONDARY)
        ok_btn.clicked.connect(dlg.accept)
        br.addWidget(ok_btn); vl.addLayout(br)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            guardar_archivo(self.paciente["id"], path, inp.text().strip())
            self._load_archivos()

    def _abrir_archivo(self, ruta):
        if os.path.exists(ruta):
            os.startfile(ruta)
        else:
            m = QMessageBox(self); m.setWindowTitle("Error")
            m.setText("Archivo no encontrado."); m.setStyleSheet("color:black; background:white;"); m.exec()

    def _eliminar_archivo(self, aid, ruta):
        m = QMessageBox(self); m.setWindowTitle("Confirmar")
        m.setText("¿Eliminar este archivo?")
        m.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        m.setStyleSheet("color:black; background:white;")
        if m.exec() == QMessageBox.StandardButton.Yes:
            eliminar_archivo(aid, ruta); self._load_archivos()

    # ── Load all ──────────────────────────────────────────────────────────────
    def _load_all(self):
        self._load_historial()
        self.odontograma.load(get_odontograma(self.paciente["id"]))
        self._load_datos_medicos()
        self._load_recetas()
        self._load_archivos()

    def _exportar_pdf(self):
        nombre = f"{self.paciente['nombre']}_{self.paciente['apellido']}"
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF", f"expediente_{nombre}.pdf", "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            exportar_pdf_expediente(
                self.paciente,
                get_historial(self.paciente["id"]),
                get_odontograma(self.paciente["id"]),
                get_recetas(self.paciente["id"]),
                get_archivos(self.paciente["id"]),
                path
            )
            m = QMessageBox(self); m.setWindowTitle("PDF Exportado")
            m.setText(f"✅ PDF guardado en:\n{path}")
            m.setStyleSheet("color:black; background:white;"); m.exec()
        except Exception as e:
            m = QMessageBox(self); m.setWindowTitle("Error")
            m.setText(f"No se pudo exportar:\n{str(e)}")
            m.setStyleSheet("color:black; background:white;"); m.exec()

    def _volver(self):
        parent = self.parent()
        if hasattr(parent, "mostrar_lista"):
            parent.mostrar_lista()

    def _make_table(self, headers):
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        if len(headers) > 1:
            t.horizontalHeader().setSectionResizeMode(len(headers)-1, QHeaderView.ResizeMode.ResizeToContents)
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.setShowGrid(False)
        t.setStyleSheet(f"""
            QTableWidget {{ background:{CARD}; border-radius:10px; border:1px solid {BORDER}; font-size:13px; }}
            QHeaderView::section {{ background:{PRIMARY}; color:white; padding:9px; font-weight:700; border:none; }}
            QTableWidget::item {{ padding:8px; color:{TEXT}; }}
            QTableWidget::item:alternate {{ background:#F8FBFC; }}
        """)
        return t


# ── Main Expedientes widget (lista de pacientes + expediente) ─────────────────
class ExpedientesWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{BG};")
        self._build()

    def showEvent(self, event):
        """Refresca la lista cada vez que se muestra el módulo."""
        super().showEvent(event)
        if hasattr(self, '_search'):
            self._buscar(self._search.text())

    def _build(self):
        self._stack_layout = QVBoxLayout(self)
        self._stack_layout.setContentsMargins(0,0,0,0)
        self._stack_layout.setSpacing(0)

        # Lista de pacientes
        self._lista_widget = self._build_lista()
        self._stack_layout.addWidget(self._lista_widget)

        # Expediente (se agrega dinámicamente)
        self._expediente_widget = None

    def _build_lista(self):
        w = QWidget(); w.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(w); lay.setContentsMargins(24,20,24,20); lay.setSpacing(14)

        title = QLabel("🦷  Expedientes Clínicos")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY};")
        lay.addWidget(title)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{BORDER};"); sep.setFixedHeight(1)
        lay.addWidget(sep)

        search = QLineEdit()
        search.setPlaceholderText("🔍  Buscar paciente por nombre o teléfono…")
        search.setStyleSheet(f"""
            QLineEdit {{
                border:1.5px solid {BORDER}; border-radius:22px;
                padding:10px 18px; font-size:14px; background:white; color:{TEXT};
            }}
            QLineEdit:focus {{ border-color:{SECONDARY}; }}
        """)
        search.textChanged.connect(self._buscar)
        lay.addWidget(search)
        self._search = search

        self._stats_lbl = QLabel()
        self._stats_lbl.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        lay.addWidget(self._stats_lbl)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border:none; background:transparent;")
        self._cards_container = QWidget()
        self._cards_container.setStyleSheet("background:transparent;")
        self._cards_layout = QGridLayout(self._cards_container)
        self._cards_layout.setSpacing(14)
        self._cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._cards_container)
        lay.addWidget(scroll)

        self._buscar("")
        return w

    def _buscar(self, texto=""):
        pacientes = obtener_pacientes(texto)
        self._stats_lbl.setText(f"{len(pacientes)} paciente(s)")

        # Clear grid
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        for i, p in enumerate(pacientes):
            card = self._make_card(p)
            self._cards_layout.addWidget(card, i // 3, i % 3)

    def _make_card(self, p):
        card = QFrame()
        card.setFixedHeight(130)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet(f"""
            QFrame {{
                background:{CARD}; border-radius:12px;
                border:1.5px solid {BORDER};
            }}
            QFrame:hover {{
                border:2px solid {PRIMARY};
                background:#F0F8FF;
            }}
        """)
        cl = QVBoxLayout(card); cl.setContentsMargins(16,12,16,12); cl.setSpacing(4)

        name = QLabel(f"👤  {p['nombre']} {p['apellido']}")
        name.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        name.setStyleSheet(f"color:{TEXT}; border:none; background:transparent;")
        cl.addWidget(name)

        tel = QLabel(f"📞  {p.get('telefono','—') or '—'}")
        tel.setStyleSheet(f"color:{MUTED}; font-size:12px; border:none; background:transparent;")
        cl.addWidget(tel)

        if p.get("alergias"):
            al = QLabel(f"⚠️  {p['alergias'][:40]}")
            al.setStyleSheet(f"color:{DANGER}; font-size:11px; border:none; background:transparent;")
            cl.addWidget(al)

        ver_btn = _btn("📋  Ver Expediente", PRIMARY, SECONDARY, h=30)
        ver_btn.clicked.connect(lambda _, pac=p: self.mostrar_expediente(pac))
        cl.addWidget(ver_btn)
        return card

    def mostrar_expediente(self, paciente):
        if self._expediente_widget:
            self._stack_layout.removeWidget(self._expediente_widget)
            self._expediente_widget.deleteLater()

        self._lista_widget.setVisible(False)
        self._expediente_widget = ExpedienteWidget(paciente, self)
        self._stack_layout.addWidget(self._expediente_widget)

    def mostrar_lista(self):
        if self._expediente_widget:
            self._stack_layout.removeWidget(self._expediente_widget)
            self._expediente_widget.deleteLater()
            self._expediente_widget = None
        self._lista_widget.setVisible(True)
        self._buscar(self._search.text())
