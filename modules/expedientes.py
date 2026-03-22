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
    QListWidgetItem, QSplitter, QApplication, QSpinBox,
    QCheckBox, QDateEdit
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QDate
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
    "sano":        ("#27AE60", "Sano"),
    "caries":      ("#E74C3C", "Caries"),
    "obturado":    ("#3498DB", "Obturado"),
    "corona":      ("#9B59B6", "Corona"),
    "ausente":     ("#7F8C8D", "Ausente"),
    "implante":    ("#F39C12", "Implante"),
    "fractura":    ("#E67E22", "Fractura"),
    "pulpotomia":  ("#E91E63", "Pulpotomía"),
    "pulpectomia": ("#FF5722", "Pulpectomía"),
    "erupcionando":("#00BCD4", "Parcialmente Erupcionado"),
}

# Estados disponibles por tipo de dentición
ESTADOS_POR_TIPO = {
    "temporal":   ["sano","caries","obturado","corona","ausente","fractura","pulpotomia","pulpectomia","erupcionando"],
    "mixta":      ["sano","caries","obturado","corona","ausente","fractura","pulpotomia","pulpectomia","erupcionando"],
    "permanente": ["sano","caries","obturado","corona","ausente","implante","fractura","erupcionando"],
}

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


# ── Dentición por tipo ────────────────────────────────────────────────────────
DENTICION = {
    "temporal": {
        "nombre": "🧒 Temporal (3-6 años)",
        "superior": [55,54,53,52,51,61,62,63,64,65],
        "inferior": [85,84,83,82,81,71,72,73,74,75],
    },
    "mixta": {
        "nombre": "👦 Mixta (7-12 años)",
        "superior": [16,55,54,53,52,51,61,62,63,64,65,26],
        "inferior": [46,85,84,83,82,81,71,72,73,74,75,36],
    },
    "permanente": {
        "nombre": "🧑 Permanente (13+ años)",
        # Sin muelas del juicio (18,28,38,48)
        "superior": list(range(17,10,-1)) + list(range(21,28)),
        "inferior": list(range(47,40,-1)) + list(range(31,38)),
    },
}

def calcular_tipo_denticion(fecha_nacimiento: str) -> str:
    """Calcula el tipo de dentición según la fecha de nacimiento."""
    try:
        from datetime import date
        nacimiento = datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date()
        hoy = date.today()
        edad = hoy.year - nacimiento.year - (
            (hoy.month, hoy.day) < (nacimiento.month, nacimiento.day)
        )
        if edad <= 6:   return "temporal"
        elif edad <= 12: return "mixta"
        else:           return "permanente"
    except Exception:
        return "permanente"


# ── Odontograma widget ────────────────────────────────────────────────────────
class OdontogramaWidget(QWidget):
    changed = pyqtSignal(int, str)

    def __init__(self, tipo="permanente", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{CARD};")
        self._buttons = {}
        self._tipo = tipo
        self._build()

    def _build(self):
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 8, 12, 8)
        self._layout.setSpacing(6)

        # Selector de tipo
        tipo_row = QHBoxLayout()
        tipo_lbl = QLabel("Tipo de dentición:")
        tipo_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600; font-size:12px; background:transparent;")
        tipo_row.addWidget(tipo_lbl)

        self._tipo_combo = QComboBox()
        for key, val in DENTICION.items():
            self._tipo_combo.addItem(val["nombre"], key)
        self._tipo_combo.setCurrentIndex(
            list(DENTICION.keys()).index(self._tipo)
        )
        self._tipo_combo.setStyleSheet(f"""
            QComboBox {{
                border:1.5px solid {BORDER}; border-radius:8px;
                padding:5px 10px; font-size:12px; background:white; color:{TEXT};
            }}
            QComboBox QAbstractItemView {{ color:{TEXT}; background:white; }}
        """)
        self._tipo_combo.currentIndexChanged.connect(self._cambiar_tipo)
        tipo_row.addWidget(self._tipo_combo)
        tipo_row.addStretch()
        self._layout.addLayout(tipo_row)

        # Leyenda
        legend = QHBoxLayout()
        legend.addStretch()
        for estado, (color, nombre) in ESTADOS_DIENTE.items():
            dot = QLabel(f"● {nombre}")
            dot.setStyleSheet(f"color:{color}; font-size:11px; font-weight:600; background:transparent;")
            legend.addWidget(dot)
        legend.addStretch()
        self._layout.addLayout(legend)

        # Contenedor de dientes
        self._dientes_widget = QWidget()
        self._dientes_widget.setStyleSheet("background:transparent;")
        self._dientes_layout = QVBoxLayout(self._dientes_widget)
        self._dientes_layout.setContentsMargins(0,0,0,0)
        self._dientes_layout.setSpacing(4)
        self._layout.addWidget(self._dientes_widget)

        self._render_dientes()

    def _render_dientes(self):
        # Limpiar dientes anteriores
        while self._dientes_layout.count():
            item = self._dientes_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self._buttons.clear()

        d = DENTICION[self._tipo]

        # Superior
        sup_lbl = QLabel("Superior")
        sup_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sup_lbl.setStyleSheet(f"color:{MUTED}; font-size:11px; background:transparent;")
        self._dientes_layout.addWidget(sup_lbl)

        sup_row = QHBoxLayout()
        sup_row.setSpacing(3)
        sup_row.addStretch()
        for n in d["superior"]:
            btn = ToothButton(n, str(n))
            btn.clicked.connect(lambda _, num=n: self._on_click(num))
            self._buttons[n] = btn
            sup_row.addWidget(btn)
        sup_row.addStretch()
        self._dientes_layout.addLayout(sup_row)

        # Separador
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background:{BORDER};"); sep.setFixedHeight(1)
        self._dientes_layout.addWidget(sep)

        # Inferior
        inf_row = QHBoxLayout()
        inf_row.setSpacing(3)
        inf_row.addStretch()
        for n in d["inferior"]:
            btn = ToothButton(n, str(n))
            btn.clicked.connect(lambda _, num=n: self._on_click(num))
            self._buttons[n] = btn
            inf_row.addWidget(btn)
        inf_row.addStretch()
        self._dientes_layout.addLayout(inf_row)

        inf_lbl = QLabel("Inferior")
        inf_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inf_lbl.setStyleSheet(f"color:{MUTED}; font-size:11px; background:transparent;")
        self._dientes_layout.addWidget(inf_lbl)

    def _cambiar_tipo(self, idx):
        self._tipo = self._tipo_combo.currentData()
        self._render_dientes()

    def set_tipo(self, tipo: str):
        """Cambia el tipo de dentición programáticamente."""
        if tipo in DENTICION:
            self._tipo = tipo
            idx = list(DENTICION.keys()).index(tipo)
            self._tipo_combo.setCurrentIndex(idx)
            self._render_dientes()

    def load(self, datos: dict):
        for num, btn in self._buttons.items():
            if num in datos:
                btn.set_estado(datos[num]["estado"])
                btn.setToolTip(f"Diente {num}: {datos[num]['estado'].capitalize()}\n{datos[num].get('notas','')}")
            else:
                btn.set_estado("sano")
                btn.setToolTip(f"Diente {num}")

    def _on_click(self, num):
        dlg = DienteDialog(num, self._buttons[num].estado, self._tipo, self)
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
    def __init__(self, numero, estado_actual, tipo_denticion="permanente", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Diente {numero}")
        self.setFixedWidth(340)
        self.setStyleSheet(f"background:{BG}; color:{TEXT};")
        self.estado = estado_actual
        self.notas  = ""
        self._tipo  = tipo_denticion
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
        # Filtrar estados según tipo de dentición
        estados_permitidos = ESTADOS_POR_TIPO.get(self._tipo, list(ESTADOS_DIENTE.keys()))
        for key in estados_permitidos:
            if key in ESTADOS_DIENTE:
                color, nombre = ESTADOS_DIENTE[key]
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
        self.tabs.addTab(self._build_periodontograma_tab(), "📊  Periodontograma")
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
    def _build_periodontograma_tab(self):
        w = QWidget(); w.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(w); lay.setContentsMargins(0,0,0,0)
        self.perio_widget = PeriodontogramaWidget(self.paciente)
        lay.addWidget(self.perio_widget)
        return w

    def _build_odontograma_tab(self):
        w = QWidget(); w.setStyleSheet(f"background:{BG};")
        lay = QVBoxLayout(w); lay.setContentsMargins(16,14,16,14); lay.setSpacing(10)

        # Detectar tipo según edad del paciente
        tipo = calcular_tipo_denticion(
            self.paciente.get("fecha_nacimiento", "") or ""
        )

        info = QLabel("Haz clic en cualquier diente para cambiar su estado. El tipo de dentición se detecta automáticamente por la edad del paciente.")
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        lay.addWidget(info)

        self.odontograma = OdontogramaWidget(tipo=tipo)
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
            import subprocess, sys
            if sys.platform == "win32":
                os.startfile(ruta)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", ruta])
            else:
                subprocess.Popen(["xdg-open", ruta])
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



# ══════════════════════════════════════════════════════════════════════════════
# PERIODONTOGRAMA COMPLETO
# ══════════════════════════════════════════════════════════════════════════════

# Superior: 17..11 | 21..27 (sin muelas del juicio)
DIENTES_SUP = [17,16,15,14,13,12,11,21,22,23,24,25,26,27]
# Inferior: 47..41 | 31..37
DIENTES_INF = [47,46,45,44,43,42,41,31,32,33,34,35,36,37]

PRONOSTICO_OPTS  = ["Bueno","Dudoso","Malo","Imposible"]
MOVILIDAD_OPTS   = ["0","I","II","III"]
FURCA_OPTS       = ["—","I","II","III"]
PRONOSTICO_COLORS = {
    "Bueno":    ("#E1F5EE","#0F6E56"),
    "Dudoso":   ("#FAEEDA","#854F0B"),
    "Malo":     ("#FCEBEB","#A32D2D"),
    "Imposible":("#D3D1C7","#444441"),
}

def _spin(min_v=0, max_v=12, w=30) -> QSpinBox:
    s = QSpinBox()
    s.setRange(min_v, max_v)
    s.setValue(0)
    s.setFixedWidth(w); s.setFixedHeight(22)
    s.setStyleSheet(f"""
        QSpinBox {{
            border:1px solid {BORDER}; border-radius:3px;
            font-size:10px; padding:0 2px;
            background:white; color:{TEXT};
        }}
        QSpinBox::up-button, QSpinBox::down-button {{ width:0px; }}
    """)
    return s

def _combo_small(opts, w=64) -> QComboBox:
    c = QComboBox()
    for o in opts: c.addItem(o)
    c.setFixedWidth(w); c.setFixedHeight(22)
    c.setStyleSheet(f"""
        QComboBox {{
            border:1px solid {BORDER}; border-radius:3px;
            font-size:9px; padding:1px 3px;
            background:white; color:{TEXT};
        }}
        QComboBox QAbstractItemView {{ color:{TEXT}; background:white; font-size:10px; }}
    """)
    return c

def _chk() -> QCheckBox:
    cb = QCheckBox()
    cb.setStyleSheet(f"""
        QCheckBox {{
            spacing: 0px;
        }}
        QCheckBox::indicator {{
            width: 28px;
            height: 20px;
            border-radius: 4px;
            border: 1.5px solid {BORDER};
            background: #F5F8FA;
        }}
        QCheckBox::indicator:unchecked {{
            background: #F5F8FA;
            border: 1.5px solid {BORDER};
            image: none;
        }}
        QCheckBox::indicator:checked {{
            background: #E74C3C;
            border: 1.5px solid #C0392B;
            image: none;
        }}
        QCheckBox::indicator:unchecked:hover {{
            background: #FDECEA;
            border: 1.5px solid #E74C3C;
        }}
    """)
    return cb

def _row_lbl(txt, color=None) -> QLabel:
    lbl = QLabel(txt)
    lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    c = color or MUTED
    lbl.setStyleSheet(f"color:{c}; font-size:9px; background:transparent; padding-right:4px;")
    lbl.setFixedWidth(68)
    return lbl

def _sec_lbl(txt, color) -> QLabel:
    lbl = QLabel(txt)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setFont(QFont("Segoe UI",10,QFont.Weight.Bold))
    lbl.setStyleSheet(f"color:{color}; background:transparent; letter-spacing:1px;")
    return lbl


class DienteCol:
    """Columna de datos para un diente en la tabla del periodontograma."""
    def __init__(self, numero:int):
        self.numero = numero
        # Superior
        self.pronostico = _combo_small(PRONOSTICO_OPTS, 70)
        self.implante   = _chk()
        self.furca      = _combo_small(FURCA_OPTS, 44)
        self.movilidad  = _combo_small(MOVILIDAD_OPTS, 44)
        # Vestibular
        self.sang_v  = _chk()
        self.sup_v   = _chk()
        self.sond_v  = _spin(0,12)
        self.mg_v    = _spin(-5,10)
        self.placa_v = _chk()
        # Palatino/Lingual
        self.placa_p = _chk()
        self.mg_p    = _spin(-5,10)
        self.sond_p  = _spin(0,12)
        self.sup_p   = _chk()
        self.sang_p  = _chk()
        self.nota    = QLineEdit()
        self.nota.setPlaceholderText("nota")
        self.nota.setFixedHeight(20)
        self.nota.setFixedWidth(70)
        self.nota.setStyleSheet(f"""
            QLineEdit {{
                border:1px solid {BORDER}; border-radius:3px;
                font-size:9px; padding:1px 3px; background:white; color:{TEXT};
            }}
        """)
        # Actualizar color de pronóstico
        self.pronostico.currentTextChanged.connect(self._update_prog_color)
        self._update_prog_color(self.pronostico.currentText())

    def _update_prog_color(self, val):
        bg, fg = PRONOSTICO_COLORS.get(val, ("#FFFFFF", TEXT))
        self.pronostico.setStyleSheet(f"""
            QComboBox {{
                border:1px solid {BORDER}; border-radius:3px;
                font-size:9px; padding:1px 3px;
                background:{bg}; color:{fg};
            }}
            QComboBox QAbstractItemView {{ color:{TEXT}; background:white; font-size:10px; }}
        """)

    def get_data(self) -> dict:
        return {
            "pronostico": self.pronostico.currentText(),
            "implante":   self.implante.isChecked(),
            "furca":      self.furca.currentText(),
            "movilidad":  self.movilidad.currentText(),
            "sang_v":     self.sang_v.isChecked(),
            "sup_v":      self.sup_v.isChecked(),
            "sond_v":     self.sond_v.value(),
            "mg_v":       self.mg_v.value(),
            "placa_v":    self.placa_v.isChecked(),
            "placa_p":    self.placa_p.isChecked(),
            "mg_p":       self.mg_p.value(),
            "sond_p":     self.sond_p.value(),
            "sup_p":      self.sup_p.isChecked(),
            "sang_p":     self.sang_p.isChecked(),
            "nota":       self.nota.text(),
        }

    def set_data(self, d:dict):
        if not d: return
        idx = PRONOSTICO_OPTS.index(d["pronostico"]) if d.get("pronostico") in PRONOSTICO_OPTS else 0
        self.pronostico.setCurrentIndex(idx)
        self.implante.setChecked(d.get("implante", False))
        idx_f = FURCA_OPTS.index(d["furca"]) if d.get("furca") in FURCA_OPTS else 0
        self.furca.setCurrentIndex(idx_f)
        idx_m = MOVILIDAD_OPTS.index(d["movilidad"]) if d.get("movilidad") in MOVILIDAD_OPTS else 0
        self.movilidad.setCurrentIndex(idx_m)
        self.sang_v.setChecked(d.get("sang_v", False))
        self.sup_v.setChecked(d.get("sup_v", False))
        self.sond_v.setValue(d.get("sond_v", 0))
        self.mg_v.setValue(d.get("mg_v", 0))
        self.placa_v.setChecked(d.get("placa_v", False))
        self.placa_p.setChecked(d.get("placa_p", False))
        self.mg_p.setValue(d.get("mg_p", 0))
        self.sond_p.setValue(d.get("sond_p", 0))
        self.sup_p.setChecked(d.get("sup_p", False))
        self.sang_p.setChecked(d.get("sang_p", False))
        self.nota.setText(d.get("nota", ""))


def _build_perio_table(dientes: list, cols: dict, seccion: str) -> QWidget:
    """
    Construye la tabla del periodontograma para una arcada.
    seccion = 'superior' o 'inferior'
    """
    is_sup = (seccion == "superior")
    azul = "#185FA5"; rojo = "#A32D2D"

    w = QWidget(); w.setStyleSheet("background:transparent;")
    lay = QVBoxLayout(w); lay.setContentsMargins(0,0,0,0); lay.setSpacing(2)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
    scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")

    inner = QWidget(); inner.setStyleSheet("background:transparent;")
    grid = QGridLayout(inner)
    grid.setSpacing(2); grid.setContentsMargins(0,0,0,0)

    # Filas
    ROWS_SUP = [
        ("Pronóstico",  None,  "pronostico"),
        ("Implante",    None,  "implante"),
        ("Furca",       None,  "furca"),
        ("Movilidad",   None,  "movilidad"),
        ("— VESTIBULAR —", azul, None),
        ("Sangrado V",  rojo,  "sang_v"),
        ("Supuración V",None,  "sup_v"),
        ("Sondaje V",   azul,  "sond_v"),
        ("Margen G. V", None,  "mg_v"),
        ("Placa V",     None,  "placa_v"),
        ("— PALATINO —", "#8E44AD", None),
        ("Placa P",     None,  "placa_p"),
        ("Margen G. P", None,  "mg_p"),
        ("Sondaje P",   azul,  "sond_p"),
        ("Supuración P",None,  "sup_p"),
        ("Sangrado P",  rojo,  "sang_p"),
        ("Nota",        None,  "nota"),
    ]
    ROWS_INF = [
        ("Pronóstico",  None,  "pronostico"),
        ("Implante",    None,  "implante"),
        ("Furca",       None,  "furca"),
        ("Movilidad",   None,  "movilidad"),
        ("— LINGUAL —", "#0F6E56", None),
        ("Sangrado L",  rojo,  "sang_p"),
        ("Supuración L",None,  "sup_p"),
        ("Sondaje L",   azul,  "sond_p"),
        ("Margen G. L", None,  "mg_p"),
        ("Placa L",     None,  "placa_p"),
        ("— VESTIBULAR —", azul, None),
        ("Placa V",     None,  "placa_v"),
        ("Margen G. V", None,  "mg_v"),
        ("Sondaje V",   azul,  "sond_v"),
        ("Supuración V",None,  "sup_v"),
        ("Sangrado V",  rojo,  "sang_v"),
        ("Nota",        None,  "nota"),
    ]
    rows = ROWS_SUP if is_sup else ROWS_INF

    # Headers de columna (números de diente)
    lbl_empty = QLabel(""); lbl_empty.setFixedWidth(72)
    grid.addWidget(lbl_empty, 0, 0)
    for ci, num in enumerate(dientes):
        lbl = QLabel(str(num))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("Segoe UI",10,QFont.Weight.Bold))
        lbl.setStyleSheet(f"""
            color:{PRIMARY}; background:{CARD};
            border:1px solid {BORDER}; border-radius:4px;
            padding:2px 0; min-width:44px;
        """)
        grid.addWidget(lbl, 0, ci+1)

    # Filas de datos
    for ri, (label, color, field) in enumerate(rows):
        row = ri + 1

        # Separator rows
        if field is None:
            sep_lbl = QLabel(label)
            sep_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            sep_lbl.setFont(QFont("Segoe UI",8,QFont.Weight.Bold))
            c = color or MUTED
            sep_lbl.setStyleSheet(f"""
                color:{c}; background:transparent;
                font-size:8px; letter-spacing:1px; padding:1px 0;
            """)
            grid.addWidget(sep_lbl, row, 0)
            for ci in range(len(dientes)):
                sep = QFrame(); sep.setFixedHeight(2)
                sep.setStyleSheet(f"background:{c}; border:none;")
                grid.addWidget(sep, row, ci+1)
            continue

        # Row label
        c = color or MUTED
        grid.addWidget(_row_lbl(label, c), row, 0)

        # Widgets por diente
        for ci, num in enumerate(dientes):
            col = cols[num]
            widget = getattr(col, field)
            cell = QWidget()
            cell.setStyleSheet("background:transparent;")
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(2,1,2,1)
            cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(widget)
            grid.addWidget(cell, row, ci+1)

    scroll.setWidget(inner)
    lay.addWidget(scroll)
    return w


class PeriodontogramaWidget(QWidget):
    """Periodontograma completo Superior (Vest/Palat) + Inferior (Ling/Vest)."""

    def __init__(self, paciente:dict, parent=None):
        super().__init__(parent)
        self.paciente    = paciente
        self.paciente_id = paciente["id"]
        self._cols_sup   = {n: DienteCol(n) for n in DIENTES_SUP}
        self._cols_inf   = {n: DienteCol(n) for n in DIENTES_INF}
        self._perio_id   = None
        self._build()
        self._cargar_existente()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12,10,12,10)
        root.setSpacing(8)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("📊  Periodontograma")
        title.setFont(QFont("Segoe UI",15,QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY}; background:transparent;")
        hdr.addWidget(title)
        hdr.addStretch()
        fecha_lbl = QLabel("Fecha:")
        fecha_lbl.setStyleSheet(f"color:{TEXT}; background:transparent; font-size:12px;")
        hdr.addWidget(fecha_lbl)
        self.fecha_input = QDateEdit()
        self.fecha_input.setDate(QDate.currentDate())
        self.fecha_input.setCalendarPopup(True)
        self.fecha_input.setFixedWidth(120)
        hdr.addWidget(self.fecha_input)
        dent_lbl = QLabel("Dentista:")
        dent_lbl.setStyleSheet(f"color:{TEXT}; background:transparent; font-size:12px;")
        hdr.addWidget(dent_lbl)
        self.dentista_input = QLineEdit()
        self.dentista_input.setPlaceholderText("Nombre del dentista")
        self.dentista_input.setFixedWidth(160)
        hdr.addWidget(self.dentista_input)
        root.addLayout(hdr)

        # ── Resumen ───────────────────────────────────────────────────────────
        self.resumen_lbl = QLabel("Media sondaje: — mm  |  % Placa: —%  |  % Sangrado: —%")
        self.resumen_lbl.setStyleSheet(f"""
            background:{CARD}; color:{TEXT};
            border:1px solid {BORDER}; border-radius:8px;
            padding:7px 14px; font-size:12px;
        """)
        root.addWidget(self.resumen_lbl)

        # ── Leyenda ───────────────────────────────────────────────────────────
        leyenda = QFrame()
        leyenda.setStyleSheet(f"""
            background:{CARD}; border:1px solid {BORDER};
            border-radius:8px;
        """)
        ley_lay = QHBoxLayout(leyenda)
        ley_lay.setContentsMargins(12,6,12,6)
        ley_lay.setSpacing(16)
        ley_title = QLabel("Referencia:")
        ley_title.setStyleSheet(f"color:{MUTED}; font-size:10px; font-weight:600; background:transparent; border:none;")
        ley_lay.addWidget(ley_title)
        items = [
            ("□", "#DEE4E8", "Sin marcar (click para marcar)"),
            ("✓", "#E74C3C", "Marcado / Presente"),
            ("Sondaje", "#185FA5", "Profundidad en mm (0-12)"),
            ("MG", MUTED, "Margen gingival mm (-5 a 10)"),
            ("I/II/III", "#8E44AD", "Grado furca o movilidad"),
            ("Bueno", "#0F6E56", "Pronóstico favorable"),
            ("Malo", "#A32D2D", "Pronóstico desfavorable"),
        ]
        for symbol, color, desc in items:
            item_w = QWidget()
            item_w.setStyleSheet("background:transparent; border:none;")
            item_lay = QHBoxLayout(item_w)
            item_lay.setContentsMargins(0,0,0,0)
            item_lay.setSpacing(4)
            sym_lbl = QLabel(symbol)
            sym_lbl.setStyleSheet(f"""
                background:{color}; color:white;
                border-radius:3px; padding:1px 5px;
                font-size:9px; font-weight:600; border:none;
            """)
            desc_lbl = QLabel(desc)
            desc_lbl.setStyleSheet(f"color:{MUTED}; font-size:9px; background:transparent; border:none;")
            item_lay.addWidget(sym_lbl)
            item_lay.addWidget(desc_lbl)
            ley_lay.addWidget(item_w)
        ley_lay.addStretch()
        root.addWidget(leyenda)

        # ── Scroll vertical principal ─────────────────────────────────────────
        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        container = QWidget(); container.setStyleSheet(f"background:{BG};")
        cont_lay = QVBoxLayout(container)
        cont_lay.setSpacing(10); cont_lay.setContentsMargins(4,4,4,4)

        # SUPERIOR
        cont_lay.addWidget(_sec_lbl("— SUPERIOR —", "#185FA5"))
        cont_lay.addWidget(_build_perio_table(DIENTES_SUP, self._cols_sup, "superior"))

        # Divisor
        div = QFrame(); div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"background:{BORDER}; border:none;"); div.setFixedHeight(2)
        cont_lay.addWidget(div)

        # INFERIOR
        cont_lay.addWidget(_sec_lbl("— INFERIOR —", "#3B6D11"))
        cont_lay.addWidget(_build_perio_table(DIENTES_INF, self._cols_inf, "inferior"))

        cont_lay.addStretch()
        main_scroll.setWidget(container)
        root.addWidget(main_scroll)

        # ── Notas + botones ───────────────────────────────────────────────────
        notas_lbl = QLabel("Notas generales:")
        notas_lbl.setStyleSheet(f"color:{TEXT}; font-weight:600; background:transparent;")
        root.addWidget(notas_lbl)
        self.notas_input = QTextEdit()
        self.notas_input.setFixedHeight(55)
        root.addWidget(self.notas_input)

        btn_row = QHBoxLayout(); btn_row.addStretch()
        limpiar_btn = _btn("🗑️  Limpiar", "#ECF0F1", "#D5DBDB", TEXT)
        limpiar_btn.clicked.connect(self._limpiar)
        btn_row.addWidget(limpiar_btn)
        guardar_btn = _btn("💾  Guardar Periodontograma", PRIMARY, SECONDARY)
        guardar_btn.clicked.connect(self._guardar)
        btn_row.addWidget(guardar_btn)
        root.addLayout(btn_row)

        # Conectar para resumen
        for col in list(self._cols_sup.values()) + list(self._cols_inf.values()):
            col.sond_v.valueChanged.connect(self._actualizar_resumen)
            col.sond_p.valueChanged.connect(self._actualizar_resumen)

    def _actualizar_resumen(self):
        all_cols = list(self._cols_sup.values()) + list(self._cols_inf.values())
        sondajes = []
        placa = 0; sangrado = 0
        total = len(all_cols)
        for c in all_cols:
            sondajes += [c.sond_v.value(), c.sond_p.value()]
            if c.placa_v.isChecked() or c.placa_p.isChecked(): placa += 1
            if c.sang_v.isChecked() or c.sang_p.isChecked(): sangrado += 1
        media = sum(sondajes)/len(sondajes) if sondajes else 0
        pct_p = placa/total*100 if total else 0
        pct_s = sangrado/total*100 if total else 0
        self.resumen_lbl.setText(
            f"Media sondaje: {media:.1f} mm  |  % Placa: {pct_p:.0f}%  |  % Sangrado: {pct_s:.0f}%"
        )

    def _cargar_existente(self):
        import json
        from database.db_manager import get_periodontogramas
        registros = get_periodontogramas(self.paciente_id)
        if not registros: return
        rec = registros[0]
        self._perio_id = rec["id"]
        if rec.get("fecha"):
            self.fecha_input.setDate(QDate.fromString(rec["fecha"], "yyyy-MM-dd"))
        self.dentista_input.setText(rec.get("dentista","") or "")
        self.notas_input.setPlainText(rec.get("notas","") or "")
        try:
            datos = json.loads(rec.get("datos_json","{}") or "{}")
            for num_str, d in datos.items():
                num = int(num_str)
                if num in self._cols_sup: self._cols_sup[num].set_data(d)
                elif num in self._cols_inf: self._cols_inf[num].set_data(d)
        except Exception:
            pass
        self._actualizar_resumen()

    def _guardar(self):
        import json
        from database.db_manager import crear_periodontograma, actualizar_periodontograma
        from PyQt6.QtWidgets import QMessageBox
        datos = {}
        for n, c in self._cols_sup.items(): datos[str(n)] = c.get_data()
        for n, c in self._cols_inf.items(): datos[str(n)] = c.get_data()
        datos_json  = json.dumps(datos, ensure_ascii=False)
        fecha       = self.fecha_input.date().toString("yyyy-MM-dd")
        dentista    = self.dentista_input.text().strip()
        notas       = self.notas_input.toPlainText().strip()
        if self._perio_id:
            actualizar_periodontograma(self._perio_id, datos_json, notas, dentista)
        else:
            self._perio_id = crear_periodontograma(
                self.paciente_id, fecha, dentista, "permanente", datos_json, notas
            )
        m = QMessageBox(self)
        m.setWindowTitle("Guardado")
        m.setText("✅ Periodontograma guardado correctamente.")
        m.setStyleSheet("color:black; background:white;"); m.exec()
        self._actualizar_resumen()

    def _limpiar(self):
        from PyQt6.QtWidgets import QMessageBox
        m = QMessageBox(self)
        m.setWindowTitle("Confirmar")
        m.setText("¿Limpiar todos los datos del periodontograma?")
        m.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        m.setStyleSheet("color:black; background:white;")
        if m.exec() == QMessageBox.StandardButton.Yes:
            for c in list(self._cols_sup.values()) + list(self._cols_inf.values()):
                c.set_data({})
            self.notas_input.clear()
            self._perio_id = None
            self._actualizar_resumen()
