from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QDialog,
    QFormLayout, QComboBox, QTextEdit, QMessageBox, QFrame,
    QHeaderView, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database.db_manager import (
    crear_paciente, obtener_pacientes,
    actualizar_paciente, eliminar_paciente, obtener_paciente_por_id
)

# ── Palette ──────────────────────────────────────────────────────────────────
PRIMARY   = "#1A6B8A"
SECONDARY = "#2196B0"
ACCENT    = "#4ECDC4"
BG        = "#F5F8FA"
CARD      = "#FFFFFF"
TEXT      = "#2C3E50"
MUTED     = "#7F8C8D"
DANGER    = "#E74C3C"
SUCCESS   = "#2ECC71"
BORDER    = "#DEE4E8"


def _btn(label: str, color: str, hover: str, text_color: str = "white") -> QPushButton:
    b = QPushButton(label)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    b.setStyleSheet(f"""
        QPushButton {{
            background: {color}; color: {text_color};
            border: none; border-radius: 6px;
            padding: 8px 18px; font-size: 13px; font-weight: 600;
        }}
        QPushButton:hover {{ background: {hover}; }}
        QPushButton:pressed {{ opacity: 0.85; }}
    """)
    return b


# ── Dialog: add / edit patient ────────────────────────────────────────────────
class PacienteDialog(QDialog):
    def __init__(self, parent=None, paciente: dict = None):
        super().__init__(parent)
        self.paciente = paciente
        self.setWindowTitle("Nuevo Paciente" if not paciente else "Editar Paciente")
        self.setMinimumWidth(520)
        self.setStyleSheet(f"background:{CARD}; color:{TEXT};")
        self._build()
        if paciente:
            self._fill(paciente)

    def _field(self, placeholder="") -> QLineEdit:
        f = QLineEdit()
        f.setPlaceholderText(placeholder)
        f.setStyleSheet(f"""
            QLineEdit {{
                border: 1.5px solid {BORDER}; border-radius: 6px;
                padding: 7px 10px; font-size: 13px; background: {BG};
            }}
            QLineEdit:focus {{ border-color: {SECONDARY}; background: white; }}
        """)
        return f

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(28, 24, 28, 24)

        # Title
        title = QLabel("Nuevo Paciente" if not self.paciente else "Editar Paciente")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY};")
        layout.addWidget(title)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color:{BORDER};"); layout.addWidget(sep)

        form = QFormLayout(); form.setSpacing(10)
        label_style = f"font-size:13px; color:{TEXT}; font-weight:600;"

        def lbl(t): l = QLabel(t); l.setStyleSheet(label_style); return l

        self.nombre    = self._field("Ej. Carlos")
        self.apellido  = self._field("Ej. García")
        self.fecha_nac = self._field("YYYY-MM-DD")
        self.telefono  = self._field("Ej. 555-0100")
        self.email     = self._field("correo@ejemplo.com")
        self.direccion = self._field("Calle, Ciudad")
        self.num_seguro= self._field("Número de seguro (opcional)")

        self.genero = QComboBox()
        self.genero.addItems(["", "Masculino", "Femenino", "Otro"])
        self.genero.setStyleSheet(f"""
            QComboBox {{
                border: 1.5px solid {BORDER}; border-radius: 6px;
                padding: 7px 10px; font-size: 13px; background: {BG};
            }}
            QComboBox:focus {{ border-color: {SECONDARY}; }}
        """)

        self.alergias = QTextEdit()
        self.alergias.setPlaceholderText("Ej. Penicilina, látex…")
        self.alergias.setMaximumHeight(60)
        self.alergias.setStyleSheet(f"""
            QTextEdit {{
                border: 1.5px solid {BORDER}; border-radius: 6px;
                padding: 7px; font-size: 13px; background: {BG};
            }}
        """)

        self.notas = QTextEdit()
        self.notas.setPlaceholderText("Observaciones adicionales…")
        self.notas.setMaximumHeight(60)
        self.notas.setStyleSheet(self.alergias.styleSheet())

        form.addRow(lbl("Nombre *"),        self.nombre)
        form.addRow(lbl("Apellido *"),       self.apellido)
        form.addRow(lbl("Fecha Nacimiento"), self.fecha_nac)
        form.addRow(lbl("Género"),           self.genero)
        form.addRow(lbl("Teléfono"),         self.telefono)
        form.addRow(lbl("Email"),            self.email)
        form.addRow(lbl("Dirección"),        self.direccion)
        form.addRow(lbl("Nº Seguro"),        self.num_seguro)
        form.addRow(lbl("Alergias"),         self.alergias)
        form.addRow(lbl("Notas"),            self.notas)
        layout.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = _btn("Cancelar", "#ECF0F1", "#D5DBDB", TEXT)
        cancel.clicked.connect(self.reject)
        save   = _btn("💾  Guardar", PRIMARY, SECONDARY)
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel); btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _fill(self, p):
        self.nombre.setText(p.get("nombre",""))
        self.apellido.setText(p.get("apellido",""))
        self.fecha_nac.setText(p.get("fecha_nacimiento",""))
        idx = self.genero.findText(p.get("genero",""))
        self.genero.setCurrentIndex(idx if idx >= 0 else 0)
        self.telefono.setText(p.get("telefono",""))
        self.email.setText(p.get("email",""))
        self.direccion.setText(p.get("direccion",""))
        self.num_seguro.setText(p.get("numero_seguro",""))
        self.alergias.setText(p.get("alergias",""))
        self.notas.setText(p.get("notas",""))

    def _save(self):
        if not self.nombre.text().strip() or not self.apellido.text().strip():
            msg = QMessageBox(self)
            msg.setWindowTitle("Campos requeridos")
            msg.setText("Nombre y apellido son obligatorios.")
            msg.setStyleSheet("color: black; background: white;")
            msg.exec()
            return
        self.result_data = {
            "nombre":           self.nombre.text().strip(),
            "apellido":         self.apellido.text().strip(),
            "fecha_nacimiento": self.fecha_nac.text().strip(),
            "genero":           self.genero.currentText(),
            "telefono":         self.telefono.text().strip(),
            "email":            self.email.text().strip(),
            "direccion":        self.direccion.text().strip(),
            "numero_seguro":    self.num_seguro.text().strip(),
            "alergias":         self.alergias.toPlainText().strip(),
            "notas":            self.notas.toPlainText().strip(),
        }
        self.accept()


# ── Main patients widget ──────────────────────────────────────────────────────
class PacientesWidget(QWidget):
    paciente_seleccionado = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{BG};")
        self._build()
        self._load()

    def showEvent(self, event):
        super().showEvent(event)
        self._load()

    def _build(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(24, 20, 24, 20)

        # ── Header ──
        header = QHBoxLayout()
        title = QLabel("🦷  Pacientes")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{PRIMARY};")
        header.addWidget(title)
        header.addStretch()

        self.search = QLineEdit()
        self.search.setPlaceholderText("🔍  Buscar por nombre, teléfono…")
        self.search.setFixedWidth(280)
        self.search.setStyleSheet(f"""
            QLineEdit {{
                border: 1.5px solid {BORDER}; border-radius: 20px;
                padding: 7px 14px; font-size: 13px; background: white;
            }}
            QLineEdit:focus {{ border-color: {SECONDARY}; }}
        """)
        self.search.textChanged.connect(self._load)
        header.addWidget(self.search)

        refresh_btn = _btn("🔄", "#ECF0F1", "#D5DBDB", TEXT)
        refresh_btn.setToolTip("Refrescar lista")
        refresh_btn.setFixedWidth(42)
        refresh_btn.clicked.connect(self._load)
        header.addWidget(refresh_btn)

        nuevo_btn = _btn("＋  Nuevo Paciente", PRIMARY, SECONDARY)
        nuevo_btn.clicked.connect(self._nuevo)
        header.addWidget(nuevo_btn)
        root.addLayout(header)
        root.addSpacing(16)

        # ── Stats bar ──
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet(f"color:{MUTED}; font-size:12px;")
        root.addWidget(self.stats_label)
        root.addSpacing(8)

        # ── Table ──
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Apellido", "Teléfono", "Email", "Registro", "Acciones"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setMinimumSectionSize(80)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 200)
        self.table.setColumnWidth(5, 120)
        self.table.setColumnWidth(6, 100)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
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
        root.addWidget(self.table)

    def _load(self):
        q = self.search.text().strip()
        pacientes = obtener_pacientes(q)
        self.stats_label.setText(f"{len(pacientes)} paciente(s) encontrado(s)")
        self.table.setRowCount(len(pacientes))

        for row, p in enumerate(pacientes):
            fecha = p.get("fecha_registro", "")[:10] if p.get("fecha_registro") else ""
            for col, val in enumerate([
                str(p["id"]), p["nombre"], p["apellido"],
                p.get("telefono",""), p.get("email",""), fecha
            ]):
                item = QTableWidgetItem(val)
                item.setData(Qt.ItemDataRole.UserRole, p["id"])
                self.table.setItem(row, col, item)

            # Action buttons
            cell = QWidget()
            cell.setStyleSheet(f"background: transparent;")
            hb = QHBoxLayout(cell)
            hb.setContentsMargins(4, 2, 4, 2); hb.setSpacing(4)

            edit_btn = _btn("✏️", "#3498DB", "#2980B9")
            edit_btn.setFixedSize(34, 28)
            edit_btn.setToolTip("Editar")
            edit_btn.clicked.connect(lambda _, pid=p["id"]: self._editar(pid))

            del_btn = _btn("🗑", DANGER, "#C0392B")
            del_btn.setFixedSize(34, 28)
            del_btn.setToolTip("Eliminar")
            del_btn.clicked.connect(lambda _, pid=p["id"]: self._eliminar(pid))

            ver_btn = _btn("👁", "#27AE60", "#1E8449")
            ver_btn.setFixedSize(34, 28)
            ver_btn.setToolTip("Ver expediente")
            ver_btn.clicked.connect(lambda _, pid=p["id"]: self._ver_expediente(pid))

            hb.addWidget(ver_btn); hb.addWidget(edit_btn); hb.addWidget(del_btn)
            self.table.setCellWidget(row, 6, cell)

        self.table.setRowHeight(0, 44)
        for r in range(self.table.rowCount()):
            self.table.setRowHeight(r, 44)

    def _nuevo(self):
        dlg = PacienteDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            crear_paciente(dlg.result_data)
            self._load()
            msg = QMessageBox(self)
            msg.setWindowTitle("Éxito")
            msg.setText("Paciente registrado correctamente.")
            msg.setStyleSheet("color: black; background: white;")
            msg.exec()

    def _ver_expediente(self, pid: int):
        from database.db_manager import obtener_paciente_por_id as _get_pac
        p = _get_pac(pid)
        if not p:
            return
        # Buscar el ExpedientesWidget en el stack del padre
        parent = self.parent()
        while parent:
            if hasattr(parent, 'stack'):
                # Cambiar al módulo de expedientes (índice 3)
                parent._switch(3)
                # Abrir directamente el expediente del paciente
                exp_widget = parent.stack.widget(3)
                if hasattr(exp_widget, 'mostrar_expediente'):
                    exp_widget.mostrar_expediente(dict(p))
                break
            parent = parent.parent()

    def _editar(self, pid: int):
        p = obtener_paciente_por_id(pid)
        if not p:
            return
        dlg = PacienteDialog(self, p)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            actualizar_paciente(pid, dlg.result_data)
            self._load()

    def _eliminar(self, pid: int):
        p = obtener_paciente_por_id(pid)
        name = f"{p['nombre']} {p['apellido']}" if p else f"#{pid}"
        msg = QMessageBox(self)
        msg.setWindowTitle("Confirmar eliminación")
        msg.setText(f"¿Eliminar al paciente {name}?\nSus datos se archivarán.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setStyleSheet("color: black; background: white;")
        reply = msg.exec()
        if reply == QMessageBox.StandardButton.Yes:
            eliminar_paciente(pid)
            self._load()
