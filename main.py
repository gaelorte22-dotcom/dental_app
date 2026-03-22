import sys
import os
import random
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QLabel, QPushButton, QStackedWidget,
    QFrame, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt, QDate, QTime, QTimer
from PyQt6.QtGui import QFont

from database.db_manager import init_db
from modules.pacientes import PacientesWidget
from modules.citas import CitasWidget
from modules.facturacion import FacturacionWidget
from modules.expedientes import ExpedientesWidget
from license_manager import verify_license
from activation_screen import ActivationScreen
from theme import get_palette, app_stylesheet
from notificaciones import ReminderManager
from updater import verificar_actualizacion, VERSION_ACTUAL

# Frases que se muestran al abrir la app, se elige una al azar
_FRASES = [
    "Que tengas un increíble turno 🦷✨",
    "Cada sonrisa que cuidas hace la diferencia 😊",
    "Hoy es un gran día para hacer grandes cosas 💪",
    "Tu trabajo cambia la vida de tus pacientes 🌟",
    "Un día más, una sonrisa más 🦷❤️",
    "El éxito es la suma de pequeños esfuerzos diarios 🚀",
    "Hoy vas a dejar huella en tu consultorio 👊",
    "La excelencia no es un acto, es un hábito ⭐",
    "Cada paciente confía en ti — ¡a la altura! 🏆",
    "Día nuevo, energía nueva, sonrisas nuevas ✨",
]

_MESES = ["","enero","febrero","marzo","abril","mayo","junio",
          "julio","agosto","septiembre","octubre","noviembre","diciembre"]
_DIAS  = ["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]

# Colores base de la app, se repiten aqui para no importar theme en cada widget
PRIMARY    = "#1A6B8A"
SECONDARY  = "#2196B0"
ACCENT     = "#4ECDC4"
BG         = "#F5F8FA"
CARD       = "#FFFFFF"
TEXT       = "#2C3E50"
MUTED      = "#7F8C8D"
BORDER     = "#DEE4E8"
SIDEBAR_BG = "#0F3D52"
SIDEBAR_HVR= "#1A6B8A"
SIDEBAR_ACT= "#2196B0"


class SidebarButton(QPushButton):
    # Boton de navegacion del sidebar, resalta cuando esta activo
    def __init__(self, icon: str, label: str):
        super().__init__(f"  {icon}  {label}")
        self.setCheckable(True)
        self.setFixedHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 12))
        self.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:white;
                border:none; border-radius:8px;
                text-align:left; padding-left:14px;
            }}
            QPushButton:hover   {{ background:{SIDEBAR_HVR}; }}
            QPushButton:checked {{ background:{SIDEBAR_ACT}; color:white; font-weight:700; }}
        """)


class HomeWidget(QWidget):
    # Pantalla de inicio con saludo, frase del dia y accesos rapidos
    def __init__(self, switch_fn):
        super().__init__()
        self.switch_fn = switch_fn
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 40)
        root.setSpacing(22)

        hora = QTime.currentTime().hour()
        if hora < 12:   saludo = "☀️  ¡Buenos días!"
        elif hora < 18: saludo = "🌤  ¡Buenas tardes!"
        else:           saludo = "🌙  ¡Buenas noches!"

        greet = QLabel(saludo)
        greet.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        greet.setStyleSheet(f"color:{PRIMARY}; background:transparent;")
        root.addWidget(greet)

        sub = QLabel(random.choice(_FRASES))
        sub.setFont(QFont("Segoe UI", 15))
        sub.setStyleSheet(f"color:{SECONDARY}; background:transparent;")
        root.addWidget(sub)

        hoy = QDate.currentDate()
        date_lbl = QLabel(
            f"{_DIAS[hoy.dayOfWeek()-1].capitalize()}, "
            f"{hoy.day()} de {_MESES[hoy.month()]} de {hoy.year()}"
        )
        date_lbl.setFont(QFont("Segoe UI", 13))
        date_lbl.setStyleSheet(f"color:{MUTED}; background:transparent;")
        root.addWidget(date_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{BORDER}; border:none;")
        root.addWidget(sep)

        sec_lbl = QLabel("Acceso rapido")
        sec_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        sec_lbl.setStyleSheet(f"color:{TEXT}; background:transparent;")
        root.addWidget(sec_lbl)

        grid = QGridLayout()
        grid.setSpacing(16)
        cards = [
            ("👥", "Pacientes",   "Ver y gestionar pacientes", PRIMARY,   1),
            ("📅", "Citas",       "Agenda del consultorio",    SECONDARY, 2),
            ("🦷", "Expedientes", "Historial clínico",         "#27AE60", 3),
            ("💰", "Facturación", "Cobros y pagos",            "#8E44AD", 4),
        ]
        for i, (icon, title, desc, color, page) in enumerate(cards):
            card = self._make_card(icon, title, desc, color, page)
            grid.addWidget(card, i // 2, i % 2)
        root.addLayout(grid)
        root.addStretch()

        footer = QLabel(f"DentalApp v{VERSION_ACTUAL}  -  Sistema de Gestion Odontologica")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"color:{MUTED}; font-size:11px; background:transparent;")
        root.addWidget(footer)

    def _make_card(self, icon, title, desc, color, page):
        card = QWidget()
        card.setFixedHeight(120)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setStyleSheet(f"""
            QWidget {{
                background:{CARD}; border-radius:12px;
                border:1.5px solid {BORDER};
            }}
            QWidget:hover {{
                border:2px solid {color}; background:#F0F8FF;
            }}
            QLabel {{ background:transparent; border:none; }}
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(6)

        il = QLabel(icon)
        il.setFont(QFont("Segoe UI", 26))
        il.setStyleSheet("border:none; background:transparent;")
        cl.addWidget(il)

        tl = QLabel(title)
        tl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        tl.setStyleSheet(f"color:{color}; border:none; background:transparent;")
        cl.addWidget(tl)

        dl = QLabel(desc)
        dl.setFont(QFont("Segoe UI", 11))
        dl.setStyleSheet(f"color:{MUTED}; font-size:11px; border:none; background:transparent;")
        cl.addWidget(dl)

        card.mousePressEvent = lambda _, p=page: self.switch_fn(p)
        return card


class MainWindow(QMainWindow):
    def __init__(self, consultorio: str = ""):
        super().__init__()
        titulo = f"DentalApp - {consultorio}" if consultorio else "DentalApp"
        self.setWindowTitle(titulo)
        self.resize(1150, 720)
        self.setMinimumSize(900, 600)
        self._build_ui()
        self._setup_reminders()
        # Revisar actualizaciones 5 segundos despues de abrir para no bloquear el arranque
        QTimer.singleShot(5000, lambda: self._check_updates())
        QApplication.instance().setStyleSheet(app_stylesheet())

    def _check_updates(self):
        self._updater = verificar_actualizacion(self, silencioso=True)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Sidebar de navegacion
        sidebar = QWidget()
        sidebar.setFixedWidth(224)
        sidebar.setStyleSheet(f"background:{SIDEBAR_BG};")
        sb = QVBoxLayout(sidebar)
        sb.setSpacing(4)
        sb.setContentsMargins(12, 0, 12, 12)

        logo_f = QFrame()
        logo_f.setFixedHeight(72)
        logo_f.setStyleSheet("background:transparent;")
        ll = QVBoxLayout(logo_f)
        ll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lbl = QLabel("🦷 DentalApp")
        logo_lbl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lbl.setStyleSheet(f"color:{ACCENT}; letter-spacing:1px; background:transparent;")
        ll.addWidget(logo_lbl)
        sub_lbl = QLabel("Sistema de Gestión")
        sub_lbl.setFont(QFont("Segoe UI", 9))
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_lbl.setStyleSheet(f"color:{MUTED}; background:transparent;")
        ll.addWidget(sub_lbl)
        sb.addWidget(logo_f)

        sep_sb = QFrame()
        sep_sb.setFrameShape(QFrame.Shape.HLine)
        sep_sb.setFixedHeight(1)
        sep_sb.setStyleSheet(f"background:{BORDER}; border:none;")
        sb.addWidget(sep_sb)

        nav_items = [
            ("🏠", "Inicio",       0),
            ("👥", "Pacientes",    1),
            ("📅", "Citas",        2),
            ("🦷", "Expedientes",  3),
            ("💰", "Facturación",  4),
        ]
        self.nav_btns = []
        for icon, lbl, idx in nav_items:
            btn = SidebarButton(icon, lbl)
            btn.clicked.connect(lambda _, i=idx: self._switch(i))
            self.nav_btns.append(btn)
            sb.addWidget(btn)

        sb.addStretch()

        update_btn = QPushButton("  🔄  Actualizaciones")
        update_btn.setFixedHeight(42)
        update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        update_btn.setFont(QFont("Segoe UI", 11))
        update_btn.clicked.connect(lambda: verificar_actualizacion(self, silencioso=False))
        update_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:#8892A4;
                border:none; border-radius:8px;
                text-align:left; padding-left:14px;
            }}
            QPushButton:hover {{ color:white; background:rgba(255,255,255,0.08); }}
        """)
        sb.addWidget(update_btn)

        ver_lbl = QLabel(f"v{VERSION_ACTUAL}")
        ver_lbl.setFont(QFont("Segoe UI", 10))
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver_lbl.setStyleSheet(f"color:{MUTED}; background:transparent;")
        sb.addWidget(ver_lbl)
        root.addWidget(sidebar)

        # Area principal con scroll para pantallas pequenas
        stack_scroll = QScrollArea()
        stack_scroll.setWidgetResizable(True)
        stack_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        stack_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        stack_scroll.setStyleSheet("QScrollArea { border:none; background:transparent; }")

        self.stack = QStackedWidget()
        self.stack.addWidget(HomeWidget(self._switch))
        self.stack.addWidget(PacientesWidget())
        self.stack.addWidget(CitasWidget())
        self.stack.addWidget(ExpedientesWidget())
        self.stack.addWidget(FacturacionWidget())
        stack_scroll.setWidget(self.stack)
        root.addWidget(stack_scroll)
        self._switch(0)

    def _setup_reminders(self):
        self._reminder = ReminderManager(self)
        self._reminder.mostrar_popup.connect(
            lambda citas: self._reminder.mostrar(citas, self)
        )

    def _switch(self, idx: int):
        self.stack.setCurrentIndex(idx)
        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == idx)


def main():
    init_db()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 11))

    valid, info = verify_license()
    if not valid:
        activation = ActivationScreen()
        win_ref = []
        def on_activated():
            activation.close()
            w = MainWindow()
            win_ref.append(w)
            w.show()
        activation.activated.connect(on_activated)
        activation.show()
    else:
        MainWindow(consultorio=info).show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
