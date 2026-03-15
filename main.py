import sys
import os
import random
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QLabel, QPushButton, QStackedWidget, QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtGui import QFont

from database.db_manager import init_db
from modules.pacientes import PacientesWidget
from modules.citas import CitasWidget
from modules.facturacion import FacturacionWidget
from modules.expedientes import ExpedientesWidget
from license_manager import verify_license
from activation_screen import ActivationScreen
from theme import theme, get_palette, app_stylesheet
from notificaciones import ReminderManager
from updater import verificar_actualizacion

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
_DIAS  = ["lunes","martes","miércoles","jueves","viernes","sábado","domingo"]


# ── Sidebar nav button ────────────────────────────────────────────────────────
class SidebarButton(QPushButton):
    def __init__(self, icon: str, label: str):
        super().__init__(f"  {icon}  {label}")
        self.setCheckable(True)
        self.setFixedHeight(48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 12))
        self._refresh()
        theme.connect(lambda _: self._refresh())

    def _refresh(self):
        p = get_palette()
        self.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:{p['SIDEBAR_TXT']};
                border:none; border-radius:8px;
                text-align:left; padding-left:14px;
            }}
            QPushButton:hover   {{ background:{p['SIDEBAR_HVR']}; }}
            QPushButton:checked {{
                background:{p['SIDEBAR_ACT']}; color:white; font-weight:700;
            }}
        """)


# ── Dark/Light toggle button ──────────────────────────────────────────────────
class ThemeToggleButton(QPushButton):
    def __init__(self):
        super().__init__()
        self.setFixedHeight(42)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFont(QFont("Segoe UI", 11))
        self.clicked.connect(theme.toggle)
        theme.connect(lambda _: self._refresh())
        self._refresh()

    def _refresh(self):
        p = get_palette()
        if theme.is_dark():
            label = "  ☀️  Modo Claro"
            bg    = "#2D3561"; hover = "#3D4571"
        else:
            label = "  🌙  Modo Oscuro"
            bg    = "rgba(255,255,255,0.08)"; hover = "rgba(255,255,255,0.18)"
        self.setText(label)
        self.setStyleSheet(f"""
            QPushButton {{
                background:{bg}; color:{p['SIDEBAR_TXT']};
                border:1px solid rgba(255,255,255,0.15);
                border-radius:8px; text-align:left; padding-left:14px;
            }}
            QPushButton:hover {{ background:{hover}; }}
        """)


# ── Home widget ───────────────────────────────────────────────────────────────
class HomeWidget(QWidget):
    def __init__(self, switch_fn):
        super().__init__()
        self.switch_fn = switch_fn
        self._cards_meta = []
        self._build()
        theme.connect(lambda _: self._apply())

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(48, 40, 48, 40)
        root.setSpacing(22)

        hora = QTime.currentTime().hour()
        if hora < 12:   sal = "☀️  ¡Buenos días!"
        elif hora < 18: sal = "🌤  ¡Buenas tardes!"
        else:           sal = "🌙  ¡Buenas noches!"

        self.greet = QLabel(sal)
        self.greet.setFont(QFont("Segoe UI", 26, QFont.Weight.Bold))
        root.addWidget(self.greet)

        self.sub = QLabel(random.choice(_FRASES))
        self.sub.setFont(QFont("Segoe UI", 15))
        root.addWidget(self.sub)

        hoy = QDate.currentDate()
        self.date_lbl = QLabel(
            f"{_DIAS[hoy.dayOfWeek()-1].capitalize()}, "
            f"{hoy.day()} de {_MESES[hoy.month()]} de {hoy.year()}"
        )
        self.date_lbl.setFont(QFont("Segoe UI", 13))
        root.addWidget(self.date_lbl)

        self.sep = QFrame(); self.sep.setFrameShape(QFrame.Shape.HLine)
        self.sep.setFixedHeight(1); root.addWidget(self.sep)

        self.sec_lbl = QLabel("Acceso rápido")
        self.sec_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        root.addWidget(self.sec_lbl)

        grid = QGridLayout(); grid.setSpacing(16)
        card_defs = [
            ("👥", "Pacientes",   "Ver y gestionar pacientes", "#1A6B8A", 1),
            ("📅", "Citas",       "Agenda del consultorio",    "#2196B0", 2),
            ("🦷", "Expedientes", "Historial clínico",         "#27AE60", 3),
            ("💰", "Facturación", "Cobros y pagos",            "#8E44AD", 4),
        ]
        self._cards_meta = []
        for i, (icon, title, desc, color, page) in enumerate(card_defs):
            card, desc_lbl = self._make_card(icon, title, desc, color, page)
            self._cards_meta.append((card, desc_lbl, color))
            grid.addWidget(card, i // 2, i % 2)
        root.addLayout(grid)
        root.addStretch()

        self.footer = QLabel("DentalApp v1.0.0  —  Sistema de Gestión Odontológica")
        self.footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.footer)

        self._apply()

    def _make_card(self, icon, title, desc, color, page):
        card = QWidget()
        card.setFixedHeight(120)
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        cl = QVBoxLayout(card); cl.setContentsMargins(20,16,20,16); cl.setSpacing(6)

        il = QLabel(icon); il.setFont(QFont("Segoe UI", 26))
        il.setStyleSheet("border:none; background:transparent;")
        cl.addWidget(il)

        tl = QLabel(title); tl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        tl.setStyleSheet(f"color:{color}; border:none; background:transparent;")
        cl.addWidget(tl)

        dl = QLabel(desc); dl.setFont(QFont("Segoe UI", 11))
        dl.setStyleSheet("border:none; background:transparent;")
        cl.addWidget(dl)

        card.mousePressEvent = lambda _, p=page: self.switch_fn(p)
        return card, dl

    def _apply(self, _=None):
        p = get_palette()
        # Forzar fondo y color en el widget Y todos sus QLabel hijos
        self.setStyleSheet(f"""
            QWidget {{ background:{p['BG']}; color:{p['TEXT']}; }}
            QLabel  {{ background:transparent; color:{p['TEXT']}; }}
            QFrame  {{ background:{p['BG']}; }}
        """)
        self.greet.setStyleSheet(f"color:{p['PRIMARY']}; background:transparent; font-size:26px; font-weight:700;")
        self.sub.setStyleSheet(f"color:{p['SECONDARY']}; background:transparent; font-size:15px;")
        self.date_lbl.setStyleSheet(f"color:{p['MUTED']}; background:transparent; font-size:13px;")
        self.sep.setStyleSheet(f"background:{p['BORDER']}; border:none; max-height:1px;")
        self.sec_lbl.setStyleSheet(f"color:{p['TEXT']}; font-weight:700; background:transparent; font-size:13px;")
        self.footer.setStyleSheet(f"color:{p['MUTED']}; font-size:11px; background:transparent;")

        hover_bg = "#1E2A3A" if theme.is_dark() else "#F0F8FF"
        for card, desc_lbl, color in self._cards_meta:
            card.setStyleSheet(f"""
                QWidget {{
                    background:{p['CARD']}; border-radius:12px;
                    border:1.5px solid {p['BORDER']};
                }}
                QWidget:hover {{
                    border:2px solid {color};
                    background:{hover_bg};
                }}
                QLabel {{
                    background:transparent;
                    border:none;
                }}
            """)
            desc_lbl.setStyleSheet(f"color:{p['MUTED']}; font-size:11px; border:none; background:transparent;")


# ── Main window ───────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self, consultorio: str = ""):
        super().__init__()
        self.setWindowTitle(f"DentalApp — {consultorio}" if consultorio else "DentalApp")
        self.resize(1150, 720)
        self.setMinimumSize(900, 600)
        self._build_ui()
        self._setup_reminders()
        # Verificar actualizaciones 5 segundos después de abrir
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(5000, lambda: self._check_updates())
        theme.connect(self._apply_theme)
        self._apply_theme()

    def _check_updates(self):
        self._updater = verificar_actualizacion(self, silencioso=True)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setSpacing(0); root.setContentsMargins(0,0,0,0)

        # ── Sidebar ───────────────────────────────────────────────────────────
        self.sidebar = QWidget(); self.sidebar.setFixedWidth(224)
        sb = QVBoxLayout(self.sidebar)
        sb.setSpacing(4); sb.setContentsMargins(12,0,12,12)

        logo_f = QFrame(); logo_f.setFixedHeight(72)
        logo_f.setStyleSheet("background:transparent;")
        ll = QVBoxLayout(logo_f); ll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_lbl = QLabel("🦷 DentalApp")
        self.logo_lbl.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self.logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(self.logo_lbl)
        self.sub_lbl = QLabel("Sistema de Gestión")
        self.sub_lbl.setFont(QFont("Segoe UI", 9))
        self.sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ll.addWidget(self.sub_lbl)
        sb.addWidget(logo_f)

        self.sep_sb = QFrame(); self.sep_sb.setFrameShape(QFrame.Shape.HLine)
        self.sep_sb.setFixedHeight(1); sb.addWidget(self.sep_sb)

        nav_items = [
            ("🏠","Inicio",0), ("👥","Pacientes",1), ("📅","Citas",2),
            ("🦷","Expedientes",3), ("💰","Facturación",4),
        ]
        self.nav_btns = []
        for icon, lbl, idx in nav_items:
            btn = SidebarButton(icon, lbl)
            btn.clicked.connect(lambda _, i=idx: self._switch(i))
            self.nav_btns.append(btn); sb.addWidget(btn)

        sb.addStretch()

        self.theme_btn = ThemeToggleButton()
        sb.addWidget(self.theme_btn)

        # Buscar actualizaciones
        self.update_btn = QPushButton("  🔄  Actualizaciones")
        self.update_btn.setFixedHeight(42)
        self.update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_btn.setFont(QFont("Segoe UI", 11))
        self.update_btn.clicked.connect(lambda: verificar_actualizacion(self, silencioso=False))
        self.update_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:#8892A4;
                border:none; border-radius:8px;
                text-align:left; padding-left:14px;
            }}
            QPushButton:hover {{ color:white; background:rgba(255,255,255,0.08); }}
        """)
        sb.addWidget(self.update_btn)

        self.ver_lbl = QLabel("v1.0.0")
        self.ver_lbl.setFont(QFont("Segoe UI", 10))
        self.ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sb.addWidget(self.ver_lbl)
        root.addWidget(self.sidebar)

        # ── Stack ─────────────────────────────────────────────────────────────
        self.stack = QStackedWidget()
        self.stack.addWidget(HomeWidget(self._switch))   # 0
        self.stack.addWidget(PacientesWidget())          # 1
        self.stack.addWidget(CitasWidget())              # 2
        self.stack.addWidget(ExpedientesWidget())        # 3
        self.stack.addWidget(FacturacionWidget())        # 4
        root.addWidget(self.stack)
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

    def _apply_theme(self, _=None):
        p = get_palette()
        # Aplicar stylesheet global primero
        QApplication.instance().setStyleSheet(app_stylesheet())
        # Sidebar
        self.sidebar.setStyleSheet(f"background:{p['SIDEBAR_BG']};")
        self.logo_lbl.setStyleSheet(f"color:{p['ACCENT']}; letter-spacing:1px; background:transparent;")
        self.sub_lbl.setStyleSheet(f"color:{p['MUTED']}; background:transparent;")
        self.sep_sb.setStyleSheet(f"background:{p['BORDER']}; border:none;")
        self.ver_lbl.setStyleSheet(f"color:{p['MUTED']}; background:transparent;")
        # Stack / contenido
        self.stack.setStyleSheet(f"background:{p['BG']};")
        self.centralWidget().setStyleSheet(f"background:{p['BG']};")
        # Forzar repintado de toda la ventana
        self.update()
        self.repaint()

# ── Entry point ───────────────────────────────────────────────────────────────
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
            w = MainWindow(); win_ref.append(w); w.show()
        activation.activated.connect(on_activated)
        activation.show()
    else:
        MainWindow(consultorio=info).show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
