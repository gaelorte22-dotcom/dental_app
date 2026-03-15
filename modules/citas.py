from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QDialog,
    QFormLayout, QComboBox, QTextEdit, QMessageBox, QFrame,
    QHeaderView, QCalendarWidget, QTimeEdit, QSpinBox
)
from PyQt6.QtCore import Qt, QDate, QTime, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QBrush
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database.db_manager import get_connection, obtener_pacientes, obtener_paciente_por_id

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

ESTADOS = ["pendiente", "confirmada", "completada", "cancelada"]
ESTADO_COLORS = {
    "pendiente":   "#F39C12",
    "confirmada":  "#27AE60",
    "completada":  "#2196B0",
    "cancelada":   "#E74C3C",
}


def _btn(label, color, hover, text_color="white"):
    b = QPushButton(label)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(f"""
        QPushButton {{
            background: {color}; color: {text_color};
            border: none; border-radius: 6px;
            padding: 8px 18px; font-size: 13px; font-weight: 600;
        }}
        QPushButton:hover {{ background: {hover}; }}
    """)
    return b


# ── CRUD helpers ──────────────────────────────────────────────────────────────
def crear_cita(datos: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO citas (paciente_id, fecha, hora, duracion, motivo, estado, notas)
        VALUES (:paciente_id, :fecha, :hora, :duracion, :motivo, :estado, :notas)
    """, datos)
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def obtener_citas(fecha: str = None, busqueda: str = "") -> list:
    conn = get_connection()
    cur = conn.cursor()
    query = """
        SELECT c.*, p.nombre || ' ' || p.apellido AS paciente_nombre
        FROM citas c
        LEFT JOIN pacientes p ON c.paciente_id = p.id
        WHERE 1=1
    """
    params = []
    if fecha:
        query += " AND c.fecha = ?"
        params.append(fecha)
    if busqueda:
        query += " AND (p.nombre LIKE ? OR p.apellido LIKE ? OR c.motivo LIKE ?)"
        like = f"%{busqueda}%"
        params.extend([like, like, like])
    query += " ORDER BY c.fecha, c.hora"
    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def obtener_cita_por_id(cita_id: int) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.*, p.nombre || ' ' || p.apellido AS paciente_nombre
        FROM citas c LEFT JOIN pacientes p ON c.paciente_id = p.id
        WHERE c.id = ?
    """, (cita_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def actualizar_cita(cita_id: int, datos: dict):
    conn = get_connection()
    conn.execute("""
        UPDATE citas SET paciente_id=:paciente_id, fecha=:fecha, hora=:hora,
        duracion=:duracion, motivo=:motivo, estado=:estado, notas=:notas
        WHERE id=:id
    """, {**datos, "id": cita_id})
    conn.commit()
    conn.close()


def eliminar_cita(cita_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM citas WHERE id=?", (cita_id,))
    conn.commit()
    conn.close()


def fechas_con_citas() -> set:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT fecha FROM citas WHERE estado != 'cancelada'")
    fechas = {row[0] for row in cur.fetchall()}
    conn.close()
    return fechas


# ── Dialog: nueva / editar cita ───────────────────────────────────────────────
class CitaDialog(QDialog):
    def __init__(self, parent=None, cita: dict = None, fecha_default: str = None):
        super().__init__(parent)
        self.cita = cita
        self.setWindowTitle("Nueva Cita" if not cita else "Editar Cita")
        self.setMinimumWidth(480)
        self.setStyleSheet(f"background: {CARD}; color: {TEXT};")
        self._build(fecha_default)
        if cita:
            self._fill(cita)

    def _field(self, placeholder=""):
        f = QLineEdit()
        f.setPlaceholderText(placeholder)
        f.setStyleSheet(f"""
            QLineEdit {{
                border: 1.5px solid {BORDER}; border-radius: 6px;
                padding: 7px 10px; font-size: 13px; background: {BG};
                color: {TEXT};
            }}
            QLineEdit:focus {{ border-color: {SECONDARY}; background: white; }}
        """)
        return f

    def _combo_style(self):
        return f"""
            QComboBox {{
                border: 1.5px solid {BORDER}; border-radius: 6px;
                padding: 7px 10px; font-size: 13px; background: {BG};
                color: {TEXT};
            }}
            QComboBox:focus {{ border-color: {SECONDARY}; }}
            QComboBox QAbstractItemView {{ color: {TEXT}; background: white; }}
        """

    def _build(self, fecha_default):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(28, 24, 28, 24)

        title = QLabel("Nueva Cita" if not self.cita else "Editar Cita")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {PRIMARY};")
        layout.addWidget(title)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        layout.addWidget(sep)

        form = QFormLayout(); form.setSpacing(10)
        lbl_style = f"font-size:13px; color:{TEXT}; font-weight:600;"
        def lbl(t): l = QLabel(t); l.setStyleSheet(lbl_style); return l

        # Paciente
        self.paciente_combo = QComboBox()
        self.paciente_combo.setStyleSheet(self._combo_style())
        self._pacientes = obtener_pacientes()
        self.paciente_combo.addItem("-- Seleccionar paciente --", None)
        for p in self._pacientes:
            self.paciente_combo.addItem(f"{p['nombre']} {p['apellido']}", p["id"])

        # Fecha
        self.fecha = self._field("YYYY-MM-DD")
        if fecha_default:
            self.fecha.setText(fecha_default)
        else:
            self.fecha.setText(QDate.currentDate().toString("yyyy-MM-dd"))

        # Hora
        self.hora = QTimeEdit()
        self.hora.setDisplayFormat("HH:mm")
        self.hora.setTime(QTime(9, 0))
        self.hora.setStyleSheet(f"""
            QTimeEdit {{
                border: 1.5px solid {BORDER}; border-radius: 6px;
                padding: 7px 10px; font-size: 13px; background: {BG};
                color: {TEXT};
            }}
        """)

        # Duración
        self.duracion = QSpinBox()
        self.duracion.setRange(15, 180)
        self.duracion.setSingleStep(15)
        self.duracion.setValue(30)
        self.duracion.setSuffix(" min")
        self.duracion.setStyleSheet(f"""
            QSpinBox {{
                border: 1.5px solid {BORDER}; border-radius: 6px;
                padding: 7px 10px; font-size: 13px; background: {BG};
                color: {TEXT};
            }}
        """)

        # Motivo
        self.motivo = self._field("Ej. Limpieza, extracción, revisión…")

        # Estado
        self.estado = QComboBox()
        self.estado.addItems(ESTADOS)
        self.estado.setStyleSheet(self._combo_style())

        # Notas
        self.notas = QTextEdit()
        self.notas.setPlaceholderText("Observaciones adicionales…")
        self.notas.setMaximumHeight(70)
        self.notas.setStyleSheet(f"""
            QTextEdit {{
                border: 1.5px solid {BORDER}; border-radius: 6px;
                padding: 7px; font-size: 13px; background: {BG};
                color: {TEXT};
            }}
        """)

        form.addRow(lbl("Paciente *"),  self.paciente_combo)
        form.addRow(lbl("Fecha *"),     self.fecha)
        form.addRow(lbl("Hora *"),      self.hora)
        form.addRow(lbl("Duración"),    self.duracion)
        form.addRow(lbl("Motivo"),      self.motivo)
        form.addRow(lbl("Estado"),      self.estado)
        form.addRow(lbl("Notas"),       self.notas)
        layout.addLayout(form)

        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = _btn("Cancelar", "#ECF0F1", "#D5DBDB", TEXT)
        cancel.clicked.connect(self.reject)
        save = _btn("💾  Guardar", PRIMARY, SECONDARY)
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel); btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _fill(self, c):
        # Set patient
        for i in range(self.paciente_combo.count()):
            if self.paciente_combo.itemData(i) == c.get("paciente_id"):
                self.paciente_combo.setCurrentIndex(i)
                break
        self.fecha.setText(c.get("fecha", ""))
        t = QTime.fromString(c.get("hora", "09:00"), "HH:mm")
        self.hora.setTime(t)
        self.duracion.setValue(c.get("duracion", 30))
        self.motivo.setText(c.get("motivo", ""))
        idx = self.estado.findText(c.get("estado", "pendiente"))
        self.estado.setCurrentIndex(idx if idx >= 0 else 0)
        self.notas.setText(c.get("notas", ""))

    def _save(self):
        if self.paciente_combo.currentData() is None:
            msg = QMessageBox(self)
            msg.setWindowTitle("Campo requerido")
            msg.setText("Debes seleccionar un paciente.")
            msg.setStyleSheet("color: black; background: white;")
            msg.exec()
            return
        if not self.fecha.text().strip():
            msg = QMessageBox(self)
            msg.setWindowTitle("Campo requerido")
            msg.setText("La fecha es obligatoria.")
            msg.setStyleSheet("color: black; background: white;")
            msg.exec()
            return
        self.result_data = {
            "paciente_id": self.paciente_combo.currentData(),
            "fecha":       self.fecha.text().strip(),
            "hora":        self.hora.time().toString("HH:mm"),
            "duracion":    self.duracion.value(),
            "motivo":      self.motivo.text().strip(),
            "estado":      self.estado.currentText(),
            "notas":       self.notas.toPlainText().strip(),
        }
        self.accept()


# ── Main citas widget ─────────────────────────────────────────────────────────
class CitasWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background: {BG};")
        self._fecha_seleccionada = QDate.currentDate().toString("yyyy-MM-dd")
        self._build()
        self._highlight_calendar()
        self._load()

    def _build(self):
        root = QHBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(20, 20, 20, 20)

        # ── LEFT: calendar panel ──────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(10)

        cal_title = QLabel("📅  Calendario")
        cal_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        cal_title.setStyleSheet(f"color: {PRIMARY};")
        left.addWidget(cal_title)

        self.calendar = QCalendarWidget()
        self.calendar.setFixedWidth(300)
        self.calendar.setGridVisible(True)
        self.calendar.setStyleSheet(f"""
            QCalendarWidget {{
                background: {CARD}; border: 1px solid {BORDER};
                border-radius: 10px;
            }}
            QCalendarWidget QAbstractItemView {{
                color: {TEXT}; background: {CARD};
                selection-background-color: {PRIMARY};
                selection-color: white;
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: {TEXT};
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background: {PRIMARY}; border-radius: 8px;
            }}
            QCalendarWidget QToolButton {{
                color: white; background: transparent;
                font-size: 13px; font-weight: bold;
            }}
            QCalendarWidget QToolButton:hover {{ background: {SECONDARY}; border-radius:4px; }}
            QCalendarWidget QSpinBox {{ color: white; background: transparent; }}
            QCalendarWidget QAbstractItemView {{color: {TEXT};}}
        """)
        # Normalizar color de sábado y domingo igual que días de semana
        normal_fmt = QTextCharFormat()
        normal_fmt.setForeground(QBrush(QColor(TEXT)))
        from PyQt6.QtCore import Qt as _Qt
        self.calendar.setWeekdayTextFormat(_Qt.DayOfWeek.Saturday, normal_fmt)
        self.calendar.setWeekdayTextFormat(_Qt.DayOfWeek.Sunday, normal_fmt)
        self.calendar.selectionChanged.connect(self._on_date_change)
        left.addWidget(self.calendar)

        # Legend
        legend_frame = QFrame()
        legend_frame.setStyleSheet(f"background: {CARD}; border-radius: 8px; border: 1px solid {BORDER};")
        leg_layout = QVBoxLayout(legend_frame)
        leg_layout.setContentsMargins(12, 10, 12, 10)
        leg_layout.setSpacing(6)
        leg_lbl = QLabel("Estado de citas:")
        leg_lbl.setStyleSheet(f"color: {TEXT}; font-weight: 700; font-size: 12px; border: none;")
        leg_layout.addWidget(leg_lbl)
        for estado, color in ESTADO_COLORS.items():
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 16px; border: none;")
            lbl = QLabel(estado.capitalize())
            lbl.setStyleSheet(f"color: {TEXT}; font-size: 12px; border: none;")
            row.addWidget(dot); row.addWidget(lbl); row.addStretch()
            leg_layout.addLayout(row)
        left.addWidget(legend_frame)
        left.addStretch()

        root.addLayout(left)

        # ── RIGHT: citas list ─────────────────────────────────────────────────
        right = QVBoxLayout()
        right.setSpacing(10)

        # Header
        header = QHBoxLayout()
        self.title_label = QLabel()
        self.title_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.title_label.setStyleSheet(f"color: {PRIMARY};")
        header.addWidget(self.title_label)
        header.addStretch()

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Buscar paciente o motivo…")
        self.search.setFixedWidth(240)
        self.search.setStyleSheet(f"""
            QLineEdit {{
                border: 1.5px solid {BORDER}; border-radius: 20px;
                padding: 7px 14px; font-size: 13px; background: white;
                color: {TEXT};
            }}
            QLineEdit:focus {{ border-color: {SECONDARY}; }}
        """)
        self.search.textChanged.connect(self._load)
        header.addWidget(self.search)

        refresh_btn = _btn("🔄", "#ECF0F1", "#D5DBDB", TEXT)
        refresh_btn.setFixedWidth(42)
        refresh_btn.setToolTip("Refrescar")
        refresh_btn.clicked.connect(self._refresh)
        header.addWidget(refresh_btn)

        nueva_btn = _btn("＋  Nueva Cita", PRIMARY, SECONDARY)
        nueva_btn.clicked.connect(self._nueva)
        header.addWidget(nueva_btn)
        right.addLayout(header)

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet(f"color: {MUTED}; font-size: 12px;")
        right.addWidget(self.stats_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Hora", "Paciente", "Motivo", "Duración", "Estado", "Notas", "Acciones"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: {CARD}; border-radius: 10px;
                border: 1px solid {BORDER}; font-size: 13px;
            }}
            QHeaderView::section {{
                background: {PRIMARY}; color: white;
                padding: 10px; font-weight: 700; border: none;
            }}
            QTableWidget::item {{ padding: 8px; color: {TEXT}; }}
            QTableWidget::item:selected {{ background: #D6EAF8; color: {TEXT}; }}
            QTableWidget::item:alternate {{ background: #F8FBFC; }}
        """)
        right.addWidget(self.table)
        root.addLayout(right)

    def _on_date_change(self):
        self._fecha_seleccionada = self.calendar.selectedDate().toString("yyyy-MM-dd")
        self._load()

    def _refresh(self):
        self._highlight_calendar()
        self._load()

    def _highlight_calendar(self):
        # Reset all formats first
        default_fmt = QTextCharFormat()
        self.calendar.setDateTextFormat(QDate(), default_fmt)

        # Highlight dates with appointments
        highlight = QTextCharFormat()
        highlight.setBackground(QBrush(QColor(ACCENT)))
        highlight.setForeground(QBrush(QColor("white")))

        for fecha_str in fechas_con_citas():
            try:
                parts = fecha_str.split("-")
                qdate = QDate(int(parts[0]), int(parts[1]), int(parts[2]))
                self.calendar.setDateTextFormat(qdate, highlight)
            except Exception:
                pass

    def _load(self):
        fecha = self._fecha_seleccionada
        busqueda = self.search.text().strip()
        citas = obtener_citas(fecha, busqueda)

        fecha_display = self.calendar.selectedDate().toString("dd/MM/yyyy")
        self.title_label.setText(f"🗓  Citas — {fecha_display}")
        self.stats_label.setText(f"{len(citas)} cita(s) para este día")

        self.table.setRowCount(len(citas))
        for row, c in enumerate(citas):
            hora      = c.get("hora", "")
            paciente  = c.get("paciente_nombre", "—")
            motivo    = c.get("motivo", "—")
            duracion  = f"{c.get('duracion', 30)} min"
            estado    = c.get("estado", "pendiente")
            notas     = c.get("notas", "")

            for col, val in enumerate([hora, paciente, motivo, duracion, notas]):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, c["id"])
                # col mapping: 0=hora,1=paciente,2=motivo,3=duracion,4=notas (estado is col 4 widget)
                self.table.setItem(row, col if col < 4 else col + 1, item)

            # Estado badge widget
            color = ESTADO_COLORS.get(estado, MUTED)
            badge = QLabel(f"  {estado.capitalize()}  ")
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setStyleSheet(f"""
                QLabel {{
                    background: {color}; color: white;
                    border-radius: 10px; font-size: 11px;
                    font-weight: 700; padding: 3px 8px;
                }}
            """)
            badge_cell = QWidget()
            badge_cell.setStyleSheet("background: transparent;")
            bl = QHBoxLayout(badge_cell)
            bl.setContentsMargins(4, 4, 4, 4)
            bl.addWidget(badge)
            self.table.setCellWidget(row, 4, badge_cell)

            # Action buttons
            cell = QWidget()
            cell.setStyleSheet("background: transparent;")
            hb = QHBoxLayout(cell)
            hb.setContentsMargins(4, 2, 4, 2); hb.setSpacing(4)

            edit_btn = _btn("✏️", "#3498DB", "#2980B9")
            edit_btn.setFixedSize(34, 28)
            edit_btn.setToolTip("Editar cita")
            edit_btn.clicked.connect(lambda _, cid=c["id"]: self._editar(cid))

            del_btn = _btn("🗑", DANGER, "#C0392B")
            del_btn.setFixedSize(34, 28)
            del_btn.setToolTip("Eliminar cita")
            del_btn.clicked.connect(lambda _, cid=c["id"]: self._eliminar(cid))

            hb.addWidget(edit_btn); hb.addWidget(del_btn)
            self.table.setCellWidget(row, 6, cell)

        for r in range(self.table.rowCount()):
            self.table.setRowHeight(r, 44)

    def _nueva(self):
        dlg = CitaDialog(self, fecha_default=self._fecha_seleccionada)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            crear_cita(dlg.result_data)
            self._highlight_calendar()
            self._load()
            msg = QMessageBox(self)
            msg.setWindowTitle("Éxito")
            msg.setText("Cita registrada correctamente. ✅")
            msg.setStyleSheet("color: black; background: white;")
            msg.exec()

    def _editar(self, cid: int):
        c = obtener_cita_por_id(cid)
        if not c:
            return
        dlg = CitaDialog(self, cita=c)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            actualizar_cita(cid, dlg.result_data)
            self._highlight_calendar()
            self._load()

    def _eliminar(self, cid: int):
        c = obtener_cita_por_id(cid)
        nombre = c.get("paciente_nombre", f"#{cid}") if c else f"#{cid}"
        msg = QMessageBox(self)
        msg.setWindowTitle("Confirmar")
        msg.setText(f"¿Eliminar la cita de {nombre}?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setStyleSheet("color: black; background: white;")
        if msg.exec() == QMessageBox.StandardButton.Yes:
            eliminar_cita(cid)
            self._highlight_calendar()
            self._load()
