"""
theme.py
Sistema de temas claro/oscuro para DentalApp.
"""


class ThemeManager:
    def __init__(self):
        self._mode = "light"
        self._listeners = []

    def toggle(self):
        self._mode = "dark" if self._mode == "light" else "light"
        for fn in self._listeners:
            try:
                fn(self._mode)
            except Exception:
                pass

    def connect(self, fn):
        """Registra un callback que se llama cuando cambia el tema."""
        if fn not in self._listeners:
            self._listeners.append(fn)

    def disconnect(self, fn):
        self._listeners = [f for f in self._listeners if f != fn]

    def is_dark(self):
        return self._mode == "dark"

    @property
    def mode(self):
        return self._mode


# Singleton global — se crea una sola vez al importar
theme = ThemeManager()


def get_palette():
    if theme.is_dark():
        return {
            "PRIMARY":    "#4ECDC4",
            "SECONDARY":  "#45B7AA",
            "ACCENT":     "#4ECDC4",
            "BG":         "#1A1A2E",
            "CARD":       "#16213E",
            "TEXT":       "#E8EAF0",
            "MUTED":      "#8892A4",
            "DANGER":     "#FF6B6B",
            "SUCCESS":    "#51CF66",
            "WARNING":    "#FFD43B",
            "BORDER":     "#2D3561",
            "SIDEBAR_BG": "#0F0F1A",
            "SIDEBAR_HVR":"#1A1A2E",
            "SIDEBAR_ACT":"#4ECDC4",
            "SIDEBAR_TXT":"#E8EAF0",
            "INPUT_BG":   "#0F0F1A",
        }
    else:
        return {
            "PRIMARY":    "#1A6B8A",
            "SECONDARY":  "#2196B0",
            "ACCENT":     "#4ECDC4",
            "BG":         "#F5F8FA",
            "CARD":       "#FFFFFF",
            "TEXT":       "#2C3E50",
            "MUTED":      "#7F8C8D",
            "DANGER":     "#E74C3C",
            "SUCCESS":    "#27AE60",
            "WARNING":    "#F39C12",
            "BORDER":     "#DEE4E8",
            "SIDEBAR_BG": "#0F3D52",
            "SIDEBAR_HVR":"#1A6B8A",
            "SIDEBAR_ACT":"#2196B0",
            "SIDEBAR_TXT":"#FFFFFF",
            "INPUT_BG":   "#FFFFFF",
        }


def app_stylesheet():
    p = get_palette()
    return f"""
        QMainWindow, QWidget {{
            background: {p['BG']};
            color: {p['TEXT']};
        }}
        QLabel {{
            background: transparent;
            color: {p['TEXT']};
        }}
        QScrollBar:vertical {{
            background: {p['BG']}; width: 8px; border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: {p['BORDER']}; border-radius: 4px; min-height: 30px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: {p['BG']}; height: 8px; border-radius: 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: {p['BORDER']}; border-radius: 4px;
        }}
        QToolTip {{
            background: {p['CARD']}; color: {p['TEXT']};
            border: 1px solid {p['BORDER']}; padding: 4px; font-size: 12px;
        }}
    """


def app_stylesheet():
    p = get_palette()
    return f"""
        QMainWindow, QDialog {{ background:{p['BG']}; color:{p['TEXT']}; }}
        QWidget   {{ background:{p['BG']}; color:{p['TEXT']}; }}
        QLabel    {{ background:transparent; color:{p['TEXT']}; }}
        QScrollArea {{ background:transparent; border:none; }}
        QScrollArea > QWidget > QWidget {{ background:transparent; }}
        QScrollBar:vertical {{
            background:{p['BG']}; width:8px; border-radius:4px;
        }}
        QScrollBar::handle:vertical {{
            background:{p['BORDER']}; border-radius:4px; min-height:30px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0px; }}
        QScrollBar:horizontal {{
            background:{p['BG']}; height:8px; border-radius:4px;
        }}
        QScrollBar::handle:horizontal {{
            background:{p['BORDER']}; border-radius:4px;
        }}
        QToolTip {{
            background:{p['CARD']}; color:{p['TEXT']};
            border:1px solid {p['BORDER']}; padding:4px; font-size:12px;
        }}
    """
