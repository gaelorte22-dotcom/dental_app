"""
activation_screen.py
Pantalla de activación que aparece cuando no hay licencia válida.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QClipboard, QGuiApplication

from license_manager import get_hardware_id, save_license

PRIMARY  = "#1A6B8A"
SECONDARY= "#2196B0"
ACCENT   = "#4ECDC4"
BG       = "#F5F8FA"
CARD     = "#FFFFFF"
TEXT     = "#2C3E50"
MUTED    = "#7F8C8D"
BORDER   = "#DEE4E8"
DANGER   = "#E74C3C"


class ActivationScreen(QWidget):
    activated = pyqtSignal()   # emitida cuando la activación es exitosa

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DentalApp — Activación")
        self.setFixedSize(500, 480)
        self.setStyleSheet(f"background: {BG};")
        self._hw_id = get_hardware_id()
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──
        header = QWidget()
        header.setFixedHeight(110)
        header.setStyleSheet(f"background: {PRIMARY};")
        hl = QVBoxLayout(header)
        hl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo = QLabel("🦷 DentalApp")
        logo.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        logo.setStyleSheet("color: white;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(logo)

        sub = QLabel("Activación de licencia")
        sub.setStyleSheet(f"color: {ACCENT}; font-size: 13px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hl.addWidget(sub)
        root.addWidget(header)

        # ── Body ──
        body = QWidget()
        body.setStyleSheet(f"background: {BG};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(40, 30, 40, 30)
        bl.setSpacing(16)

        # Hardware ID display
        hw_frame = QFrame()
        hw_frame.setStyleSheet(f"""
            QFrame {{
                background: {CARD}; border-radius: 10px;
                border: 1.5px solid {BORDER};
            }}
        """)
        hw_layout = QVBoxLayout(hw_frame)
        hw_layout.setContentsMargins(16, 14, 16, 14)
        hw_layout.setSpacing(6)

        hw_title = QLabel("ID de tu equipo:")
        hw_title.setStyleSheet(f"color: {MUTED}; font-size: 12px; border: none; background: transparent;")
        hw_layout.addWidget(hw_title)

        hw_row = QHBoxLayout()
        self.hw_display = QLineEdit(self._hw_id)
        self.hw_display.setReadOnly(True)
        self.hw_display.setStyleSheet(f"""
            QLineEdit {{
                background: {BG}; border: 1px solid {BORDER};
                border-radius: 6px; padding: 8px 12px;
                font-size: 14px; font-weight: 700;
                color: {PRIMARY}; letter-spacing: 1px;
            }}
        """)
        hw_row.addWidget(self.hw_display)

        copy_btn = QPushButton("📋 Copiar")
        copy_btn.setFixedWidth(90)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: {ACCENT}; color: white; border: none;
                border-radius: 6px; padding: 8px; font-weight: 600;
            }}
            QPushButton:hover {{ background: #3DBDB5; }}
        """)
        copy_btn.clicked.connect(self._copy_hw_id)
        hw_row.addWidget(copy_btn)
        hw_layout.addLayout(hw_row)

        info = QLabel("📧 Envía este ID a tu proveedor para obtener tu clave de activación.")
        info.setStyleSheet(f"color: {MUTED}; font-size: 11px; border: none; background: transparent;")
        info.setWordWrap(True)
        hw_layout.addWidget(info)
        bl.addWidget(hw_frame)

        # Consultorio name
        cons_lbl = QLabel("Nombre del consultorio:")
        cons_lbl.setStyleSheet(f"color: {TEXT}; font-size: 13px; font-weight: 600;")
        bl.addWidget(cons_lbl)

        self.consultorio_input = QLineEdit()
        self.consultorio_input.setPlaceholderText("Ej. Consultorio Dental García")
        self.consultorio_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1.5px solid {BORDER}; border-radius: 8px;
                padding: 10px 14px; font-size: 13px;
                background: {CARD}; color: {TEXT};
            }}
            QLineEdit:focus {{ border-color: {SECONDARY}; }}
        """)
        bl.addWidget(self.consultorio_input)

        # License key input
        key_lbl = QLabel("Clave de activación:")
        key_lbl.setStyleSheet(f"color: {TEXT}; font-size: 13px; font-weight: 600;")
        bl.addWidget(key_lbl)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXXXXXX-XXXXXXXX-XXXXXXXX-XXXXXXXX")
        self.key_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1.5px solid {BORDER}; border-radius: 8px;
                padding: 10px 14px; font-size: 13px; letter-spacing: 1px;
                background: {CARD}; color: {TEXT};
            }}
            QLineEdit:focus {{ border-color: {SECONDARY}; }}
        """)
        bl.addWidget(self.key_input)

        # Activate button
        activate_btn = QPushButton("🔓  Activar DentalApp")
        activate_btn.setFixedHeight(44)
        activate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        activate_btn.setStyleSheet(f"""
            QPushButton {{
                background: {PRIMARY}; color: white; border: none;
                border-radius: 8px; font-size: 14px; font-weight: 700;
            }}
            QPushButton:hover {{ background: {SECONDARY}; }}
        """)
        activate_btn.clicked.connect(self._activate)
        bl.addWidget(activate_btn)

        root.addWidget(body)

    def _copy_hw_id(self):
        QGuiApplication.clipboard().setText(self._hw_id)
        msg = QMessageBox(self)
        msg.setWindowTitle("Copiado")
        msg.setText("ID copiado al portapapeles ✅\nEnvíalo a tu proveedor para obtener tu clave.")
        msg.setStyleSheet("color: black; background: white;")
        msg.exec()

    def _activate(self):
        consultorio = self.consultorio_input.text().strip()
        key = self.key_input.text().strip().upper()

        if not consultorio:
            msg = QMessageBox(self)
            msg.setWindowTitle("Campo requerido")
            msg.setText("Por favor escribe el nombre del consultorio.")
            msg.setStyleSheet("color: black; background: white;")
            msg.exec()
            return

        if not key:
            msg = QMessageBox(self)
            msg.setWindowTitle("Campo requerido")
            msg.setText("Por favor ingresa la clave de activación.")
            msg.setStyleSheet("color: black; background: white;")
            msg.exec()
            return

        success = save_license(self._hw_id, key, consultorio)
        if success:
            msg = QMessageBox(self)
            msg.setWindowTitle("¡Activado!")
            msg.setText(f"✅ DentalApp activado correctamente\npara {consultorio}.\n\n¡Bienvenido!")
            msg.setStyleSheet("color: black; background: white;")
            msg.exec()
            self.activated.emit()
        else:
            msg = QMessageBox(self)
            msg.setWindowTitle("Clave inválida")
            msg.setText("❌ La clave de activación no es válida para este equipo.\n\nVerifica que la clave sea correcta\no contacta a tu proveedor.")
            msg.setStyleSheet("color: black; background: white;")
            msg.exec()
